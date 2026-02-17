from dataclasses import fields
import importlib


def define_env(env):  # type: ignore
    """
    This is the hook where you define your custom macros.
    """

    print("🚀 Macros are loading successfully!")

    @env.macro
    def dataclass_table(class_path: str) -> str:
        # 1. Dynamically import the class
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)

        # 2. Build the Markdown table
        rows = ["| Attribute | Type | Default |", "| :--- | :--- | :--- |"]

        for field in fields(cls):
            # Clean up type names (e.g., <class 'int'> -> int)
            type_name = getattr(field.type, "__name__", str(field.type))
            default = (
                field.default
                if field.default != cls.__dataclass_fields__[field.name].default_factory
                else "factory"
            )

            rows.append(f"| **{field.name}** | `{type_name}` | {default} |")

        return "\n".join(rows)
