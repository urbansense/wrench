import inspect
import os
from pathlib import Path


class PromptManager:
    @staticmethod
    def get_prompt(file_name: str):
        """
        Get the prompt from the /prompts directory.

        Retrieves prompts from the `/prompts` directory under the directory of the
        caller function. If your code needs to retrieve prompts, make sure that its
        prompts are stored under the prompts folder under the same directory.
        """
        # Get the frame of the caller
        caller_frame = inspect.stack()[1]
        caller_file_path = Path(caller_frame.filename)
        # Use the directory of the calling file
        templates_dir = caller_file_path.parent / "prompts"

        with open(os.path.join(templates_dir, file_name), "r") as f:
            prompt = f.read()

        return prompt
