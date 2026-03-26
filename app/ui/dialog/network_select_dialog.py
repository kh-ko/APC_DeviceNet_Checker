import qdarktheme

from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox)
from PySide6.QtSerialPort import QSerialPortInfo # COM 포트 인식을 위해 추가

from app.model.global_define import NetworkType
from app.ui.components.custom.custom_controls import CustomComboBox, CustomSpinBox, CustomLineEdit, CustomDialogButtonBox

# --- 연결 설정 다이얼로그 클래스 ---
class NetworkSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("장치 연결 설정")
        self.resize(350, 400)

        # 메인 레이아웃 및 폼 레이아웃 설정
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)

        # 1. 위젯 생성
        self.network_combo = CustomComboBox()
        self.network_combo.addItems([net.value for net in NetworkType])
        
        self.comport_combo = CustomComboBox()
        # 현재 PC에서 사용 가능한 COM 포트 목록을 가져와 콤보박스에 추가
        for port in QSerialPortInfo.availablePorts():
            port_name = port.portName()
            description = port.description()
            
            # 설명이 존재하면 "COM3 - USB Serial Device" 형태로, 없으면 "COM3"만 표시
            display_text = f"{port_name} - {description}" if description else port_name
            
            # addItem(화면에_보일_글자, 내부적으로_저장할_실제_데이터)
            self.comport_combo.addItem(display_text, port_name)
        
        self.address_spin = CustomSpinBox()
        self.address_spin.setRange(1, 255) # 주소 범위 설정
        
        self.ip_input = CustomLineEdit()
        self.ip_input.setPlaceholderText("예: 192.168.0.1")
        
        self.port_spin = CustomSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(5000)
        
        self.termination_combo = CustomComboBox()
        self.termination_combo.addItems(["CR+LF", "CR", "LF"])
        
        self.baudrate_combo = CustomComboBox()
        self.baudrate_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baudrate_combo.setCurrentText("115200")
        
        self.databits_combo = CustomComboBox()
        self.databits_combo.addItems(["8", "7"])
        
        self.parity_combo = CustomComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        
        self.stopbits_combo = CustomComboBox()
        self.stopbits_combo.addItems(["1", "2"])

        # 2. 폼 레이아웃에 위젯 추가 (라벨과 함께 배치됨)
        self.form_layout.addRow("Network:", self.network_combo)
        self.form_layout.addRow("Comport:", self.comport_combo)
        self.form_layout.addRow("Address:", self.address_spin)
        self.form_layout.addRow("IP:", self.ip_input)
        self.form_layout.addRow("Port:", self.port_spin)
        self.form_layout.addRow("Termination:", self.termination_combo)
        self.form_layout.addRow("BaudRate:", self.baudrate_combo)
        self.form_layout.addRow("DataBits:", self.databits_combo)
        self.form_layout.addRow("Parity:", self.parity_combo)
        self.form_layout.addRow("StopBits:", self.stopbits_combo)

        # 3. 연결하기 / 취소 버튼 추가 (QDialogButtonBox 사용)
        self.button_box = CustomDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("연결하기")
        self.button_box.button(QDialogButtonBox.Cancel).setText("취소")
        self.button_box.accepted.connect(self.accept) # Ok 누르면 다이얼로그 승인
        self.button_box.rejected.connect(self.reject) # Cancel 누르면 다이얼로그 취소
        self.layout.addWidget(self.button_box)

        # 4. 이벤트 연결 및 초기 화면 업데이트
        self.network_combo.currentIndexChanged.connect(self.update_visibility)
        self.update_visibility() # 창이 처음 뜰 때 초기 상태 반영

    # Network 선택에 따라 위젯 숨기기/보이기
    def update_visibility(self):
        net = self.network_combo.currentText()
        
        # 헬퍼 함수: 위젯과 그에 딸린 라벨을 같이 숨기거나 보여줍니다.
        def set_row_visible(widget, visible):
            widget.setVisible(visible)
            label = self.form_layout.labelForField(widget)
            if label:
                label.setVisible(visible)

        # 조건에 맞춰 표시/숨김 처리
        set_row_visible(self.comport_combo, net != NetworkType.ETHERNET.value)
        set_row_visible(self.address_spin, net == NetworkType.RS485.value)
        set_row_visible(self.ip_input, net == NetworkType.ETHERNET.value)
        set_row_visible(self.port_spin, net == NetworkType.ETHERNET.value)
        
        show_serial = net in [NetworkType.RS232.value, NetworkType.RS485.value]
        set_row_visible(self.baudrate_combo, show_serial)
        set_row_visible(self.databits_combo, show_serial)
        set_row_visible(self.parity_combo, show_serial)
        set_row_visible(self.stopbits_combo, show_serial)
        set_row_visible(self.termination_combo, show_serial)
        

    # 선택된 정보들을 딕셔너리 형태로 반환하는 함수
    def get_connection_info(self):
        net = self.network_combo.currentText()
        info = {
            "Network": net
        }
        
        if net != NetworkType.ETHERNET.value:
            info["Comport"] = self.comport_combo.currentData()
        if net == NetworkType.RS485.value:
            info["Address"] = self.address_spin.value()
        if net == NetworkType.ETHERNET.value:
            info["IP"] = self.ip_input.text()
            info["Port"] = self.port_spin.value()
        if net in [NetworkType.RS232.value, NetworkType.RS485.value]:
            info["Termination"] = self.termination_combo.currentText()
            info["BaudRate"] = self.baudrate_combo.currentText()
            info["DataBits"] = self.databits_combo.currentText()
            info["Parity"] = self.parity_combo.currentText()
            info["StopBits"] = self.stopbits_combo.currentText()
            
        return info