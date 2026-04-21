import unittest
from unittest.mock import patch, Mock

from PyQt5.QtWidgets import QApplication

import src.component_library as comp_lib


class ComponentLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls._app = QApplication([])

    def setUp(self):
        # instantiate the library widget
        self.lib = comp_lib.ComponentLibrary()
        # simple component dict used across tests
        self.component = {
            "id": 123,
            "s_no": "1",
            "name": "PUMP",
            "parent": "Pumps",
            "legend": "",
            "suffix": "",
            "object": "PUMP",
            "grips": []
        }
        # prevent actual reload from starting threads during tests
        self.lib.reload_components = Mock()

    @patch("src.component_library.QDialog.exec_", return_value=1)  # QDialog.Accepted
    @patch("src.component_library.QLineEdit.text", side_effect=["NEWPUMP", "Pumps", "L", "S"]) 
    @patch("src.component_library.api_client.update_component")
    @patch("src.component_library.QMessageBox.information")
    def test_open_edit_component_dialog_calls_update(self, mock_info, mock_update, mock_text, mock_exec):
        mock_update.return_value = Mock(status_code=200)

        # Call edit flow
        self.lib._open_edit_component_dialog(self.component)

        # update_component should be called once with component id and payload
        self.assertTrue(mock_update.called)
        called_args = mock_update.call_args[0]
        self.assertEqual(called_args[0], 123)

        # reload_components should be triggered on success
        self.lib.reload_components.assert_called()

    @patch("src.component_library.QMessageBox.question", return_value=comp_lib.QMessageBox.Yes)
    @patch("src.component_library.api_client.delete_component")
    @patch("src.component_library.QMessageBox.information")
    def test_delete_component_calls_api_when_confirmed(self, mock_info, mock_delete, mock_question):
        mock_delete.return_value = Mock(status_code=204)

        self.lib._delete_component(self.component)

        mock_delete.assert_called_once_with(123)
        self.lib.reload_components.assert_called()

    @patch("src.component_library.QMessageBox.warning")
    def test_delete_component_with_missing_id_warns(self, mock_warn):
        comp = {"name": "NoID"}
        self.lib._delete_component(comp)
        mock_warn.assert_called_once()

    @patch("src.component_library.QDialog.exec_", return_value=1)
    @patch("src.component_library.QLineEdit.text", side_effect=["", "", "", ""]) 
    @patch("src.component_library.QMessageBox.warning")
    def test_edit_component_requires_name_and_parent(self, mock_warn, mock_text, mock_exec):
        # Provide component with id but dialog returns empty fields
        self.lib._open_edit_component_dialog(self.component)
        mock_warn.assert_called()


if __name__ == "__main__":
    unittest.main()
