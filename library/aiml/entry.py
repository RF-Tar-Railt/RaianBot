from library.aiml import Kernel
from pathlib import Path
from typing import Optional
from library.translate import BaseTrans
from library.aiml.lang_support import is_include_chinese


class AIML:
    translator: BaseTrans
    client: Kernel

    def __init__(
            self,
            trans: BaseTrans,
            **bot_predicate: str
    ):
        self.translator = trans
        self.client = Kernel()
        for k, v in bot_predicate.items():
            self.client.set_bot_predicate(k, v)

    def load_aiml(self, files_dir: str, brain_path: Optional[str] = None):
        if brain_path and Path(brain_path).exists():
            self.client.bootstrap(brain_file=brain_path)
        else:
            self.client.bootstrap(
                learn_files="startup.xml", commands="LOAD ALICE",
                chdir=files_dir
            )
            self.client.save_brain(brain_path)

    def setting(self, **bot_predicate: str):
        for k, v in bot_predicate.items():
            self.client.set_bot_predicate(k, v)

    async def chat(self, message: str, session_id: Optional[str] = None):
        if is_include_chinese(message):
            message = await self.translator.trans(message, 'en')
        resp = self.client.respond(message, session_id)
        return await self.translator.trans(resp, 'zh')
