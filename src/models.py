from typing import List


class ProcessModel:
    def __init__(self, convert: bool, rename: bool, files: List[str], target: str, platform: str) -> None:
        super(ProcessModel, self).__init__()
        self.convert = convert
        self.rename = rename
        self.files = files
        self.target = target
        self.targetPlatform = platform
        self.count = len(files)
