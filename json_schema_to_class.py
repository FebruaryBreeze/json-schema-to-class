import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import lazy_write


class Config:
    indent: int = 4
    line_break: str = '\n'


def spaces(level: int):
    return ' ' * Config.indent * level


def indent_line(line: str, level: int):
    return spaces(level=level) + line if line else ''


def indent_class(code: str, level: int):
    return Config.line_break.join(indent_line(line, level) for line in code.splitlines())


class Item:
    def __init__(self, name: str):
        self.name = name

    def to_json(self):
        pairs = []
        for key in dir(self):
            if not key.startswith('_'):
                value = getattr(self, key)
                if not callable(value):
                    pairs.append((key, value))
        return dict(pairs)

    def class_name(self):
        return self.name.title().replace('_', '')

    def type_name(self):
        return self.class_name()

    def to_init_code(self) -> str:
        raise NotImplementedError  # pragma: no cover

    def to_class_code(self, level: int = 0) -> str:
        raise NotImplementedError  # pragma: no cover


class Basic(Item):
    TYPE_MAP = {
        'integer': int,
        'number': float,
        'string': str,
        'array': list,
        'object': dict,
        'boolean': bool
    }

    def __init__(self, name: str, type: type, default: Any = None):
        super().__init__(name=name)
        self.type = type
        self.default = default

    def type_name(self):
        return self.type.__name__

    def to_init_code(self) -> str:
        return f'{spaces(2)}self.{self.name}: {self.type_name()} = values.get("{self.name}", {repr(self.default)})'

    def to_class_code(self, level: int = 0):
        raise ValueError(f'Cannot convert [{self.type_name()}] to class!')


class Definition(Item):
    def __init__(self, name: str, path: str):
        super().__init__(name=name)
        self.path = path

    def to_init_code(self) -> str:
        return f'{spaces(2)}self.{self.name} = {self.class_name()}(values=values.get("{self.name}"))'

    def to_class_code(self, level: int = 0) -> str:
        raise ValueError(f'Cannot convert [{self.type_name()}] to class!')


class Array(Basic):
    use_list: bool = False

    def __init__(self, name: str, items: Item = None, default: Any = None):
        super().__init__(name=name, type=list, default=default)
        self.items = items

    def to_json(self):
        return {
            **super().to_json(),
            'items': self.items.to_json()
        }

    def type_name(self):
        Array.use_list = True
        return f'List[{self.items.type_name()}]'

    def to_init_code(self) -> str:
        if isinstance(self.items, Basic):
            return '{spaces}self.{name}: {type_name} = values.get("{name}", {default})'.format(
                spaces=spaces(2),
                name=self.name,
                type_name=self.type_name(),
                default=repr(self.default or [])
            )
        else:
            return '{spaces}self.{name}: {type_name} = list(map({item_type}, values.get("{name}", {default})))'.format(
                spaces=spaces(2),
                name=self.name,
                type_name=self.type_name(),
                item_type=self.items.type_name(),
                default=repr(self.default or [])
            )

    def to_class_code(self, level: int = 0) -> str:
        result = [f'class {self.class_name()}:']
        if isinstance(self.items, Model):
            result.append(self.items.to_class_code(level=1))
        result.append(f'{spaces(1)}def __init__(self, values: list = None):')
        result.append(f'{spaces(2)}values = values if values is not None else []')
        result.append(f'{spaces(2)}self.items: {self.type_name()} = [')
        result.append(f'{spaces(3)}{self.items.type_name()}(values=value) for value in values')
        result.append(f'{spaces(2)}]')
        code = Config.line_break.join(result)
        return indent_class(code=code, level=level)


class Model(Item):
    def __init__(self, name: str):
        super().__init__(name=name)
        self.properties: List[Item] = []
        self._in_definitions = False

    def set_in_definitions(self):
        self._in_definitions = True

    def inner_models(self) -> List['Model']:
        return [item for item in self.properties if isinstance(item, Model)]

    def to_json(self):
        return {
            **super().to_json(),
            'properties': dict((item.name, item.to_json()) for item in self.properties)
        }

    def to_init_code(self):
        prefix = '' if self._in_definitions else 'self.'
        return f'{spaces(2)}self.{self.name} = {prefix}{self.class_name()}(values=values.get("{self.name}", None))'

    def to_class_code(self, level: int = 0) -> str:
        result = [f'class {self.class_name()}:']
        for item in self.inner_models():
            result.append(item.to_class_code(level=1))
            result.append('')
        result.append(f'{spaces(1)}def __init__(self, values: dict = None):')
        result.append(f'{spaces(2)}values = values if values is not None else {{}}')
        result.append(Config.line_break.join(item.to_init_code() for item in self.properties))

        return indent_class(code=Config.line_break.join(result), level=level)


class Parser:
    def __init__(self):
        self.definitions: Dict[str, Item] = {}
        self.root: Optional[Item] = None

    def parse_object(self, name: str, schema: dict) -> Model:
        model = Model(name=name)
        for name, definition in schema.get('properties', {}).items():
            item = self.parse_definition(name=name, schema=definition)
            model.properties.append(item)
        return model

    def parse_array(self, name: str, schema: dict) -> Array:
        items = self.parse_definition('items', schema['items'])
        return Array(name=name, items=items, default=schema.get('default', None))

    def parse_definition(self, name: str, schema: dict) -> Item:
        default = schema.get('default', None)

        if 'type' in schema:
            item_type = schema['type']
            if item_type == 'object' and 'properties' in schema:
                return self.parse_object(name=name, schema=schema)
            elif item_type == 'array':
                return self.parse_array(name=name, schema=schema)
            else:
                return Basic(name=name, type=Basic.TYPE_MAP[item_type], default=default)
        elif 'enum' in schema:
            enum_list = schema['enum']
            assert len(enum_list) > 0, "Enum List is Empty"
            first = enum_list[0]
            assert all(type(first) == type(item) for item in enum_list), "Items in Enum List with Different Types"
            assert type(first) in {int, float, str}, "Enum Type is not int, float or string"
            return Basic(name=name, type=type(first), default=default)
        elif '$ref' in schema:
            path = schema['$ref']
            name = self.definitions[path].name
            return Definition(name=name, path=path)
        else:
            raise ValueError(f'Cannot parse schema {repr(schema)}')

    def parse(self, schema: dict):
        for name, definition in schema.get('definitions', {}).items():
            item = self.parse_definition(name=name, schema=definition)
            self.definitions[f'#/definitions/{name}'] = item
            if isinstance(item, Model):
                item.set_in_definitions()

        name = schema['title']
        self.root = self.parse_definition(name=name, schema=schema)

    def generate(self) -> str:
        Array.use_list = False
        result = []
        for _, definition in self.definitions.items():
            result.append(definition.to_class_code(level=0))
            result.append('')
            result.append('')
        result.append(self.root.to_class_code(level=0))

        if Array.use_list:
            result = ['from typing import List', '', ''] + result
        return Config.line_break.join(result) + Config.line_break


def generate_code(schema_path: Path) -> str:
    with open(str(schema_path)) as f:
        schema = json.load(f)

    parser = Parser()
    parser.parse(schema=schema)
    return parser.generate()


def generate_file(schema_path: Path, output_path: Path):
    lazy_write.write(output_path, generate_code(schema_path))


def generate_dir(schema_dir: Path, output_dir: Path):
    output_dir.mkdir(exist_ok=True, parents=True)

    generate_modules = []
    for schema_path in schema_dir.glob('*.json'):
        output_path = output_dir / schema_path.with_suffix('.py').name
        generate_file(schema_path=schema_path, output_path=output_path)
        generate_modules.append(f'from .{output_path.stem} import *')

    generate_modules.sort()
    init_content = Config.line_break.join(generate_modules) + Config.line_break
    init_path = output_dir / '__init__.py'
    lazy_write.write(init_path, init_content)


def to_json(obj):
    if obj is None:
        return None
    elif type(obj) in {int, float, str}:
        return obj
    elif isinstance(obj, list):
        return [to_json(item) for item in obj]
    else:
        ret = {key: to_json(value) for key, value in vars(obj).items()}
        if list(ret.keys()) == ['items'] and isinstance(ret['items'], list):  # for array class
            ret = ret['items']
        return ret


def main():  # pragma: no cover
    arg_parser = argparse.ArgumentParser(description='JSON Schema to Python Class')
    arg_parser.add_argument('schema_path', type=str)
    arg_parser.add_argument('-o', '--output-path', type=str, default=None)
    arg_parser.add_argument('-i', '--indent', type=int, default=4)

    arguments = arg_parser.parse_args()
    Config.indent = arguments.indent

    if arguments.output_path is None:
        print(generate_code(arguments.schema_path))
    else:
        generate_file(Path(arguments.schema_path), Path(arguments.output_path))


def cli():  # pragma: no cover
    init_code_lines = (
        "from pathlib import Path",
        "",
        "import json_schema_to_class",
        "",
        "current_dir: Path = Path(__file__).parent",
        "json_schema_to_class.generate_dir(",
        "    schema_dir=current_dir.parent / 'schema',",
        "    output_dir=current_dir / 'build'",
        ")",
        "",
        "if __name__ != '__main__':",
        "    from .build import *  # noqa: F403",
        "",
        "    del json_schema_to_class",
        "    del current_dir",
        "    del Path",
    )

    arg_parser = argparse.ArgumentParser(description='JSON Schema to Python Class')
    arg_parser.add_argument('command', type=str, choices=['init', 'compile', 'print'])

    arguments = arg_parser.parse_args()
    command: str = arguments.command
    if command == 'print':
        print(Config.line_break.join(init_code_lines))
    elif command == 'init':
        configs_dir = Path('./configs')
        configs_dir.mkdir(parents=True, exist_ok=True)
        init_path = configs_dir / '__init__.py'
        init_content = Config.line_break.join(init_code_lines) + Config.line_break
        lazy_write.write(init_path, init_content)
    elif command == 'compile':
        print(r'Please run [find . -path "*/configs/__init__.py" -exec python3 {} \;]')


if __name__ == '__main__':
    main()  # pragma: no cover
