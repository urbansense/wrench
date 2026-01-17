"""Configuration management utilities."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigLoader:
    """Manages loading and resolving configuration files."""

    def __init__(self, env_file: Path | str | None = None):
        """Initialize the config loader.

        Args:
            env_file: Path to .env file. If None, searches for .env in common locations
        """
        if env_file:
            load_dotenv(env_file)
        else:
            # Try common locations
            for location in [".env", "test_script/.env", Path.home() / ".wrench.env"]:
                if Path(location).exists():
                    load_dotenv(location)
                    break

    def load_yaml(self, config_path: Path | str) -> dict[str, Any]:
        """Load a YAML configuration file with environment variable resolution.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Parsed configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            content = f.read()

        # Resolve environment variables
        content = self._resolve_env_vars(content)

        return yaml.safe_load(content)

    def _resolve_env_vars(self, content: str) -> str:
        """Replace ${VAR_NAME} with environment variable values.

        Args:
            content: String content with potential env var references

        Returns:
            Content with resolved environment variables
        """
        import re

        def replace_env_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))

        return re.sub(r"\$\{([^}]+)\}", replace_env_var, content)

    def get_component_config(
        self, component_type: str, component_name: str | None = None
    ) -> Path:
        """Get the path to a component configuration file.

        Args:
            component_type: Type of component (harvester, grouper, cataloger, etc.)
            component_name: Specific component name (optional)

        Returns:
            Path to configuration file

        Raises:
            FileNotFoundError: If configuration doesn't exist
        """
        # Look in test_script first for backwards compatibility
        if component_name:
            test_script_path = Path("test_script") / f"{component_name}_config.yaml"
            if test_script_path.exists():
                return test_script_path

        # Look in tools/fixtures/configs
        if component_name:
            tools_path = (
                Path("tools/fixtures/configs")
                / component_type
                / f"{component_name}.yaml"
            )
            if tools_path.exists():
                return tools_path

        raise FileNotFoundError(
            f"Configuration for {component_type}/{component_name} not found"
        )

    def list_configs(self, component_type: str | None = None) -> list[Path]:
        """List available configuration files.

        Args:
            component_type: Filter by component type (optional)

        Returns:
            List of configuration file paths
        """
        configs = []

        # Search test_script directory
        test_script_dir = Path("test_script")
        if test_script_dir.exists():
            configs.extend(test_script_dir.glob("*_config.yaml"))

        # Search tools/fixtures/configs
        tools_config_dir = Path("tools/fixtures/configs")
        if tools_config_dir.exists():
            if component_type:
                configs.extend((tools_config_dir / component_type).glob("*.yaml"))
            else:
                configs.extend(tools_config_dir.rglob("*.yaml"))

        return sorted(set(configs))
