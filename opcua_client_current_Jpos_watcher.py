import math

from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QScrollArea
from PyQt5.QtCore import QTimer
from opcua import Client
import sys

class OPCUAClientApp(QWidget):
    def __init__(self):
        super(OPCUAClientApp, self).__init__()

        self.layout = QVBoxLayout()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)
        self.scroll.setWidget(self.scrollWidget)
        self.layout.addWidget(self.scroll)

        self.client = Client("opc.tcp://10.0.0.225:5001")  # Update this to your server's address and port
        self.client.connect()

        # Get the namespace index
        uri = 'https://UiT-remote-control-project.no'
        idx = self.client.get_namespace_index(uri)

        # List of variable names you are interested in. Update this list accordingly.
        self.variables = [
            "Current Base", "Current Shoulder", "Current Elbow", "Current Wrist 1",
            "Current Wrist 2", "Current Wrist 3"
        ]

        self.opcua_vars = {}
        i = 3
        for var_name in self.variables:
            try:
                node_path = f"ns={idx};i={i}"
                self.opcua_vars[var_name] = self.client.get_node(node_path)
                i += 1
            except Exception as e:
                print(e)

        self.labels = {}
        for var_name in self.variables:
            self.labels[var_name] = QLabel(f"{var_name}: ")
            self.scrollLayout.addWidget(self.labels[var_name])

        try:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_values)
            self.timer.start(1)  # Update every 0.001 second
        except Exception as e:
            print(e)

        self.setLayout(self.layout)

    def update_values(self):
        for var_name, var_node in self.opcua_vars.items():
            try:
                value = var_node.get_value()
                self.labels[var_name].setText(f"{var_name}: {value*180/math.pi:.2f}")
            except Exception as e:
                print(f"Error updating {var_name}: {str(e)}")

    def closeEvent(self, event):
        self.client.disconnect()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OPCUAClientApp()
    window.show()
    sys.exit(app.exec_())
