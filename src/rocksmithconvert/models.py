from typing import List


class ProcessModel:
    def __init__(
        self,
        files: List[str],
        target: str,
        platform: str,
        renameScheme: str,
        appId: str,
        overwrite: bool,
    ) -> None:
        super(ProcessModel, self).__init__()
        self.files = files
        self.target = target
        self.targetPlatform = platform
        self.renameScheme = renameScheme
        self.count = len(files)
        self.appId = appId
        self.overwrite = overwrite
