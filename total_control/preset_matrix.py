from __future__ import annotations

from dataclasses import dataclass


DEFAULT_PROJECT_DIR = "/path/to/project"
DEFAULT_REMOTE_PROJECT_DIR = "/home/{user}/project"
DEFAULT_DATA_ROOT = "/path/to/datasets"


@dataclass(frozen=True)
class PresetExperiment:
    estimated_mib: int
    dataset: str
    arch: str
    ablation: str
    dino: str
    batch_size: int
    priority: str

    @property
    def key(self) -> str:
        return "|".join([self.arch, self.ablation, self.dino, str(self.batch_size)])


def dataset_rank(dataset: str) -> int:
    return {"LEVIR": 0, "CLCD": 1, "SYSU": 2, "UAVCD+": 3, "UAVCDp": 3}.get(dataset, 9)


def make_session_name(dataset: str, arch: str, ablation: str, dino: str) -> str:
    dino_short = dino.replace("dinov2_", "d2_")
    dino_short = dino_short.replace("dinov3_", "d3_")
    dino_short = dino_short.replace("dino_", "d1_")
    dino_short = dino_short.replace("_lvd1689m", "")
    dino_short = dino_short.replace("_sat493m", "_sat")
    name = f"{dataset}_{arch}_{ablation}_{dino_short}".lower().replace("+", "p")
    return "".join(char if char.isalnum() or char in ("-", "_", ".") else "_" for char in name)


def experiments_for_dataset(dataset: str) -> list[PresetExperiment]:
    specs = [
        (10121, "resnet18", "AB", "dinov2_vitl14_reg", 16, "P1"),
        (10112, "resnet18", "AB", "dinov3_vitl16_sat493m", 16, "P1"),
        (10112, "resnet18", "AB", "dinov3_vitl16_lvd1689m", 16, "P1"),
        (9027, "resnet18", "AB", "dinov3_convnext_large_lvd1689m", 16, "P1"),
        (8921, "resnet18", "AB", "dinov3_vitb16_lvd1689m", 16, "P1"),
        (8918, "resnet18", "AB", "dino_vitb16", 16, "P1"),
        (8917, "resnet18", "AB", "dinov2_vitb14_reg", 16, "P1"),
        (8721, "resnet18", "AB", "dino_xcit_medium_24_p16", 16, "P1"),
        (8452, "resnet18", "AB", "dinov3_convnext_base_lvd1689m", 16, "P1"),
        (9454, "resnet34", "AB", "dinov2_vitb14_reg", 16, "P2"),
        (8892, "resnet18", "D", "dinov2_vitb14_reg", 16, "P2"),
        (15481, "resnet50", "AB", "dinov2_vitb14_reg", 16, "P2"),
        (7930, "resnet18", "G", "dinov2_vitb14_reg", 16, "P2"),
        (4348, "resnet18", "H", "dinov2_vitb14_reg", 16, "P2"),
        (3912, "resnet18", "A", "dinov2_vitb14_reg", 16, "P2"),
        (3402, "resnet18", "F", "dinov2_vitb14_reg", 16, "P2"),
        (2068, "resnet18", "E", "dinov2_vitb14_reg", 16, "P2"),
        (7209, "resnet18", "C", "none", 16, "P3"),
        (6497, "resnet18", "B", "none", 16, "P3"),
        (1411, "resnet18", "I", "none", 16, "P3"),
    ]
    return [
        PresetExperiment(
            estimated_mib=estimated_mib,
            dataset=dataset,
            arch=arch,
            ablation=ablation,
            dino=dino,
            batch_size=batch_size,
            priority=priority,
        )
        for estimated_mib, arch, ablation, dino, batch_size, priority in specs
    ]


def generate_experiments(datasets: str) -> list[PresetExperiment]:
    selected = [item.strip() for item in datasets.split(",") if item.strip()]
    experiments: list[PresetExperiment] = []
    for dataset in selected:
        experiments.extend(experiments_for_dataset(dataset))
    priority_rank = {"P1": 0, "P2": 1, "P3": 2}
    experiments.sort(
        key=lambda item: (
            priority_rank.get(item.priority, 9),
            dataset_rank(item.dataset),
            -item.estimated_mib,
        )
    )
    return experiments
