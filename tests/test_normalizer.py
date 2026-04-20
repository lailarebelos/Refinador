import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

from normalizer import build_config, normalize


def _write_sample_qsf(path: Path) -> None:
    payload = {
        "SurveyElements": [
            {
                "Element": "SQ",
                "Payload": {
                    "DataExportTag": "Q1",
                    "QuestionText": "Qual seu genero?",
                    "QuestionType": "MC",
                    "Selector": "SAVR",
                    "Choices": {
                        "1": {"Display": "Masculino"},
                        "2": {"Display": "Feminino"},
                    },
                    "ChoiceOrder": [1, 2],
                },
            },
            {
                "Element": "SQ",
                "Payload": {
                    "DataExportTag": "Q2",
                    "QuestionText": "Conte um comentario sobre o atendimento.",
                    "QuestionType": "TE",
                    "Selector": "SL",
                    "Choices": {},
                    "ChoiceOrder": [],
                },
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_sample_xlsx(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.cell(1, 1, "Q1")
    sheet.cell(1, 2, "Q2")
    sheet.cell(2, 1, "Qual seu genero?")
    sheet.cell(2, 2, "Conte um comentario sobre o atendimento.")
    sheet.cell(3, 1, "1")
    sheet.cell(3, 2, "Muito bom")
    sheet.cell(4, 1, "2")
    sheet.cell(4, 2, "Precisa melhorar")
    workbook.save(path)


class NormalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tempdir.name)
        self.qsf_path = self.base / "survey.qsf"
        self.xlsx_path = self.base / "export.xlsx"
        self.output_path = self.base / "normalized.xlsx"
        _write_sample_qsf(self.qsf_path)
        _write_sample_xlsx(self.xlsx_path)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_build_config_maps_qsf_types(self) -> None:
        config, df = build_config(str(self.xlsx_path), str(self.qsf_path))

        self.assertEqual(list(df.columns), ["Q1", "Q2"])
        config_by_id = {row["original_id"]: row for row in config}

        self.assertEqual(config_by_id["Q1"]["type"], "single_choice")
        self.assertEqual(config_by_id["Q2"]["type"], "open_text")
        self.assertEqual(config_by_id["Q1"]["group"], "Q1")
        self.assertEqual(config_by_id["Q2"]["alternatives"], "Texto livre")

    def test_normalize_generates_expected_workbook(self) -> None:
        config, df = build_config(str(self.xlsx_path), str(self.qsf_path))

        result = normalize(str(self.xlsx_path), str(self.output_path), config, df)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["columns"], 2)

        workbook = load_workbook(self.output_path)
        self.assertEqual(workbook.sheetnames, ["Data", "Codebook"])

        data_sheet = workbook["Data"]
        codebook_sheet = workbook["Codebook"]

        self.assertEqual(data_sheet["A1"].value, "Q1_Genero_Perfil_Respondente")
        self.assertEqual(data_sheet["B1"].value, "Q2_Conte_Comentario_Sobre")
        self.assertEqual(data_sheet["A2"].value, 1)
        self.assertEqual(data_sheet["B3"].value, "Precisa melhorar")
        self.assertEqual(codebook_sheet["A2"].value, "Q1_Genero_Perfil_Respondente")
        self.assertEqual(codebook_sheet["D3"].value, "Campo aberto")


if __name__ == "__main__":
    unittest.main()
