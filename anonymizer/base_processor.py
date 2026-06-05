from pathlib import Path
from typing import List


class BaseProcessor:
    def extract_blocks(self, input_path: Path, **kwargs) -> List[str]:
        raise NotImplementedError

    def reconstruct_and_write_anonymized_file(
        self,
        output_path: Path,
        final_processed_blocks: List[str],
        original_input_path: Path,
        **kwargs,
    ) -> None:
        raise NotImplementedError