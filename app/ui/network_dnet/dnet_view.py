import os
import json
import qdarktheme

from pathlib import Path  # 파일 맨 위쪽 import 영역에 추가
from PySide6.QtCore import QObject, QThread, Signal, Qt, Slot
from PySide6.QtWidgets import QProgressDialog, QMessageBox, QDialog, QHBoxLayout, QTabWidget, QWidget, QVBoxLayout, QScrollArea, QFormLayout, QInputDialog

from app.file_helper.file_helper import get_dnet_schema_path
from app.model.global_define import NetworkType
from app.model.dnet.dnet_model import DnetModel, CyclicItem, ExplicitItem, AccessType, DataType, UiType

from app.network_service.dnet_i7565dnm_svc import DnetI7565DNMSvc

from app.ui.components.composit.console_widget import MsgType
from app.ui.components.custom.custom_controls import CustomSpinBox, CustomLabel, CustomPushButton
from app.ui.network_view import NetworkView
from app.ui.dialog.schema_select_dialog import SchemaSelectDialog
from app.ui.dialog.slave_select_dialog import SlaveSelectDialog
from app.ui.network_dnet.item_edit_dialog import ItemEditDialog

from app.ui.network_dnet.item_widget import ItemWidget, ItemType

class DnetView(NetworkView):
    """
    DnetModel의 데이터를 읽어와 Poll-In, Poll-Out, Explicit 메시지를 
    탭 형태로 보여주는 커스텀 위젯입니다.
    """
    sig_connect_module = Signal(int)
    sig_scan_slave = Signal()
    sig_connect_slave = Signal(int, int, int)
    sig_disconnect_module = Signal()
    sig_start_polling = Signal(int)
    sig_stop_polling = Signal()
    sig_write_poll_out = Signal(bytes)
    sig_req_explicit = Signal(int, int, int, int, bytes)
    
    sig_add_log = Signal(MsgType, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress_dialog = None
        self.scan_progress_dialog = None
        self.current_schema_path = None

        self.dnet_svc = DnetI7565DNMSvc()

        self.dnet_svc.sig_add_log.connect(self.sig_add_log)
        self.dnet_svc.sig_connect_network_finished.connect(self.on_connect_network_finished)
        self.dnet_svc.sig_connect_slave_finished.connect(self.on_connect_slave_finished)
        self.dnet_svc.sig_scan_slave_finished.connect(self.on_scan_slave_finished)
        self.dnet_svc.poll_rx_signal.connect(self.on_poll_rx)
        self.dnet_svc.explicit_rx_signal.connect(self.on_explicit_rx)

        self.sig_connect_module.connect(self.dnet_svc.connect_module)
        self.sig_scan_slave.connect(self.dnet_svc.search_devices)
        self.sig_connect_slave.connect(self.dnet_svc.connect_slave)
        self.sig_disconnect_module.connect(self.dnet_svc.disconnect_module)
        self.sig_start_polling.connect(self.dnet_svc.start_polling)
        self.sig_stop_polling.connect(self.dnet_svc.stop_polling)
        self.sig_write_poll_out.connect(self.dnet_svc.write_poll_out_data)
        self.sig_req_explicit.connect(self.dnet_svc.req_explicit)

        self._init_ui()

        self.destroyed.connect(lambda: self.shutdown())

    ################################
    # public APIs
    ################################
    def shutdown(self):
        self.sig_add_log.emit(MsgType.INFO, "[DnetView][shutdown]")
        self.sig_disconnect_module.emit()

        self.on_connect_network_canceled()
        self.on_scan_slave_canceled()

    def connect_network(self, conn_info):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][connect_network] conn_info: {conn_info.get('Comport', '')}")

        """
        i7564DNM 모듈에 연결 
        """
        # connection_dialog에서 내부 데이터로 찐 포트명(예: "COM5") 반환
        port_str = conn_info.get("Comport", "COM1")
        port_num = int("".join(filter(str.isdigit, port_str)))

        self.progress_dialog = QProgressDialog("모듈에 연결 중입니다...", "취소", 0, 0, self)
        self.progress_dialog.setWindowTitle("잠시만 기다려주세요")
        self.progress_dialog.setWindowModality(Qt.WindowModal)  # 다른 UI 조작 차단
        self.progress_dialog.setMinimumDuration(0) # 즉시 표시
        
        # 취소 버튼을 눌렀을 때의 처리 (필요에 따라 연결 취소 시그널 발생 등)
        self.progress_dialog.canceled.connect(self.on_connect_network_canceled)
        
        self.progress_dialog.show()

        # 1. 마스터 활성화 (포트 오픈) - 시그널을 통한 안전한 호출
        self.sig_connect_module.emit(port_num)        

    def create_new_schema(self):
        schema_name = QInputDialog.getText(self.parent(), "새 스키마", "스키마 이름을 입력하세요:")
        if schema_name[1]:
            schema_name = schema_name[0]
            self.sig_add_log.emit(MsgType.INFO, f"[DnetView][create_new_schema] schema_name: {schema_name}")
        else:
            self.sig_add_log.emit(MsgType.INFO, f"[DnetView][create_new_schema] 취소됨")
            return False

        schema_path = get_dnet_schema_path()
        schema_path = os.path.join(schema_path, schema_name + ".json")

        if os.path.exists(schema_path):
            QMessageBox.warning(self, "경고", "이미 존재하는 스키마입니다.")
            return False

        with open(schema_path, "w") as f:
            json.dump({
                "poll-out":[],
                "poll-in":[],
                "explicit": []
            }, f)

        self.__build_ui(schema_path)
        
    def open_select_schema(self):
        dialog = SchemaSelectDialog(NetworkType.DNET.value)
        if dialog.exec() == QDialog.Accepted:
            schema_path = dialog.selected_schema
        else:
            self.sig_add_log.emit(MsgType.INFO, f"[DnetView][connect_network] 스키마 파일 선택 취소")
            return

        self.__build_ui(schema_path)
        
    def save_schema(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][save_schema]")
        if not self.current_schema_path:
            QMessageBox.warning(self, "경고", "저장할 스키마 파일이 없습니다.")
            return

        data = {"poll-in": [], "poll-out": [], "explicit": []}
        # 레이아웃을 순회하며 ItemWidget에서 JSON 데이터 수집
        for layout_name, layout in [("poll-in", self.poll_in_layout), 
                                    ("poll-out", self.poll_out_layout), 
                                    ("explicit", self.explicit_layout)]:
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, ItemWidget):
                    data[layout_name].append(widget.make_json())

        try:
            with open(self.current_schema_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            self.sig_add_log.emit(MsgType.INFO, "스키마가 성공적으로 저장되었습니다.")
            QMessageBox.information(self, "저장 완료", "스키마가 정상적으로 저장되었습니다.")
            
        except Exception as e:
            # 실패 시 로그를 남기고 알림창 표시
            self.sig_add_log.emit(MsgType.ERROR, f"스키마 저장 중 오류 발생: {e}")
            QMessageBox.critical(self, "저장 실패", f"스키마를 저장하는 중 오류가 발생했습니다:\n{e}")
        
    def save_as_schema(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][save_as_schema]")

        schema_name = QInputDialog.getText(self.parent(), "새 스키마", "스키마 이름을 입력하세요:")
        if schema_name[1]:
            schema_name = schema_name[0]
            self.sig_add_log.emit(MsgType.INFO, f"[DnetView][save_as_schema] schema_name: {schema_name}")
        else:
            self.sig_add_log.emit(MsgType.INFO, f"[DnetView][save_as_schema] 취소됨")
            return False

        schema_path = get_dnet_schema_path()
        schema_path = os.path.join(schema_path, schema_name + ".json")

        if os.path.exists(schema_path):
            QMessageBox.warning(self, "경고", "이미 존재하는 스키마입니다.")
            return False

        data = {"poll-in": [], "poll-out": [], "explicit": []}
        for layout_name, layout in [("poll-in", self.poll_in_layout), 
                                    ("poll-out", self.poll_out_layout), 
                                    ("explicit", self.explicit_layout)]:
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, ItemWidget):
                    data[layout_name].append(widget.make_json())

        try:
            with open(schema_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            self.sig_add_log.emit(MsgType.INFO, "스키마가 성공적으로 저장되었습니다.")
            QMessageBox.information(self, "저장 완료", "스키마가 정상적으로 저장되었습니다.")
        except Exception as e:
            self.sig_add_log.emit(MsgType.ERROR, f"스키마 저장 중 오류 발생: {e}")
            QMessageBox.critical(self, "저장 실패", f"스키마를 저장하는 중 오류가 발생했습니다:\n{e}")

        self.__build_ui(schema_path)
        
    def remove_schema(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][remove_schema]")
        
        if not self.current_schema_path:
            QMessageBox.warning(self, "경고", "삭제할 스키마 파일이 없습니다.")
            return

        # 정말 삭제하겠는지 한번 더 확인하는 메세지 박스 띄우기
        reply = QMessageBox.question(self, "삭제 확인", "정말 삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(self.current_schema_path)
                self.sig_add_log.emit(MsgType.INFO, "스키마가 성공적으로 삭제되었습니다.")
                QMessageBox.information(self, "삭제 완료", "스키마가 정상적으로 삭제되었습니다.")
                self.__build_ui(None)
            except Exception as e:
                self.sig_add_log.emit(MsgType.ERROR, f"스키마 삭제 중 오류 발생: {e}")
                QMessageBox.critical(self, "삭제 실패", f"스키마를 삭제하는 중 오류가 발생했습니다:\n{e}")
        
    ################################
    # Ui signal handlers
    ################################
    @Slot()
    def on_connect_network_canceled(self):
        print("[DnetView][on_connect_network_canceled]")
        self.sig_disconnect_module.emit()
        if self.progress_dialog:
            self.progress_dialog.reset()
            self.progress_dialog = None

    @Slot()
    def on_scan_slave_canceled(self):
        print("[DnetView][on_scan_slave_canceled]")
        self.sig_disconnect_module.emit()        
        if self.scan_progress_dialog:
            self.scan_progress_dialog.reset()
            self.scan_progress_dialog = None

    @Slot()
    def _on_start_polling_clicked(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][_on_start_polling_clicked]")
        cycle_time = self.spin_cycle.value()
        self.sig_start_polling.emit(cycle_time)

    @Slot()
    def _on_stop_polling_clicked(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][_on_stop_polling_clicked]")
        self.sig_stop_polling.emit()

    @Slot()
    def _on_write_out_clicked(self):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][_on_write_out_clicked]")
        
        buffer : bytearray = None

        if self.poll_out_layout.count() > 1:
            widget = self.poll_out_layout.itemAt(self.poll_out_layout.count() - 2).widget()
            if isinstance(widget, ItemWidget):
                buffer_size = widget.offset + widget.size
                buffer = bytearray(buffer_size)

        for i in range(self.poll_out_layout.count()):
            widget = self.poll_out_layout.itemAt(i).widget()
            if isinstance(widget, ItemWidget):
                widget.get_bytes_data(buffer)

        final_buffer = bytes(buffer)

        for i in range(self.poll_out_layout.count()):
            widget = self.poll_out_layout.itemAt(i).widget()
            if isinstance(widget, ItemWidget):
                widget.update_read_data(final_buffer)
        
        self.sig_write_poll_out.emit(final_buffer)

    ################################
    # Service signal handlers
    ################################
    @Slot(bool)
    def on_connect_network_finished(self, success: bool):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][on_connect_network_finished] success: {success}")
        
        if self.progress_dialog:
            self.progress_dialog.reset()
            self.progress_dialog = None

        if success:
            self.sig_add_log.emit(MsgType.INFO, "모듈에 연결되었습니다.")
        else:
            self.sig_add_log.emit(MsgType.ERROR, "모듈에 연결할 수 없습니다.")
            return

        self.scan_progress_dialog = QProgressDialog("Slave 검색 중입니다.", "취소", 0, 0, self)
        self.scan_progress_dialog.setWindowTitle("잠시만 기다려주세요")
        self.scan_progress_dialog.setWindowModality(Qt.WindowModal)  # 다른 UI 조작 차단
        self.scan_progress_dialog.setMinimumDuration(0) # 즉시 표시
        
        # 취소 버튼을 눌렀을 때의 처리 (필요에 따라 연결 취소 시그널 발생 등)
        self.scan_progress_dialog.canceled.connect(self.on_scan_slave_canceled)
        
        self.scan_progress_dialog.show()

        # 1. 마스터 활성화 (포트 오픈) - 시그널을 통한 안전한 호출
        self.sig_scan_slave.emit()  
        
    @Slot(bool)
    def on_scan_slave_finished(self, found_devices):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][on_scan_slave_finished] found_devices num: {len(found_devices)}")
        
        if self.scan_progress_dialog:
            self.scan_progress_dialog.reset()
            self.scan_progress_dialog = None

        dialog = SlaveSelectDialog(found_devices)
        if dialog.exec() == QDialog.Accepted:
            mac_id, in_len, out_len = dialog.selected_device_info
            self.sig_connect_slave.emit(mac_id, in_len, out_len)
        else:
            return

    def on_connect_slave_finished(self, success: bool):
        self.sig_add_log.emit(MsgType.INFO, f"[DnetView][on_connect_slave_finished] success: {success}")

        if success:
            self.sig_add_log.emit(MsgType.INFO, "Slave에 연결되었습니다.")
        else:
            self.sig_add_log.emit(MsgType.ERROR, "Slave에 연결할 수 없습니다.")
            return

        """
        스키마 파일을 선택하여 화면을 구성한다.
        """
        dialog = SchemaSelectDialog(NetworkType.DNET.value)
        if dialog.exec() == QDialog.Accepted:
            schema_path = dialog.selected_schema
        else:
            self.sig_add_log.emit(MsgType.INFO, f"[DnetView][connect_network] 스키마 파일 선택 취소")
            return

        self.__build_ui(schema_path)

    @Slot(int, int, bytes)
    def on_poll_rx(self, mac_id: int, con_type: int, raw_bytes: bytes):
        for i in range(self.poll_in_layout.count()):
            widget = self.poll_in_layout.itemAt(i).widget()
            if isinstance(widget, ItemWidget):
                widget.update_read_data(raw_bytes)

    def on_explicit_rx(self, service_code, class_id, instance_id, attribute_id, data, is_ok):
        if service_code != 14:
            return

        for i in range(self.explicit_layout.count()):
            widget = self.explicit_layout.itemAt(i).widget()
            if isinstance(widget, ItemWidget):
                if widget.class_id == class_id and widget.instance_id == instance_id and widget.attribute_id == attribute_id:
                    widget.update_read_data(data)
        
    ################################
    # private functions
    ################################            
    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- 상단 컨트롤 패널 추가 ---
        self.top_control_layout = QHBoxLayout()
        self.top_control_layout.setContentsMargins(5, 5, 5, 5)
        self.top_control_layout.setSpacing(10)

        # 1. 이름 라벨
        # 모델에 이름 속성이 있다면 self.dnet_model.name 등으로 변경 가능합니다.
        self.lbl_name = CustomLabel("이름 : DNET 장치") 
        self.top_control_layout.addWidget(self.lbl_name)
        
        # 2. 사이클 주기 입력 (ms)
        self.top_control_layout.addWidget(CustomLabel("사이클 주기:"))
        self.spin_cycle = CustomSpinBox()
        self.spin_cycle.setRange(1, 10000) # 1ms ~ 10000ms 범위 설정
        self.spin_cycle.setValue(1000)      # 기본값 100ms
        self.spin_cycle.setSuffix(" ms")   # 숫자 뒤에 'ms' 텍스트 표시
        self.top_control_layout.addWidget(self.spin_cycle)
        
        # 3. Polling 시작 버튼
        self.btn_start_polling = CustomPushButton("Polling 시작")
        self.btn_start_polling.clicked.connect(self._on_start_polling_clicked)
        self.top_control_layout.addWidget(self.btn_start_polling)
        
        # 4. Polling 중지 버튼
        self.btn_stop_polling = CustomPushButton("Polling 중지")
        self.btn_stop_polling.clicked.connect(self._on_stop_polling_clicked)
        self.top_control_layout.addWidget(self.btn_stop_polling)
        
        # 5. Out 데이터 쓰기 버튼
        self.btn_write_out = CustomPushButton("Out 데이터 쓰기")
        self.btn_write_out.clicked.connect(self._on_write_out_clicked)
        self.top_control_layout.addWidget(self.btn_write_out)
        
        # 남는 우측 여백을 밀어주어 위젯들을 좌측 정렬되게 함
        self.top_control_layout.addStretch() 
        
        # 메인 레이아웃에 상단 컨트롤 패널 추가 (탭 위젯보다 먼저 추가되어야 상단에 위치함)
        self.main_layout.addLayout(self.top_control_layout)

        # 탭 위젯 생성
        self.tab_widget = QTabWidget(self)
        self.main_layout.addWidget(self.tab_widget)
        
        # 각 통신 영역별 스크롤 가능한 탭 생성
        self.poll_in_tab, self.poll_in_layout = self._create_scrollable_tab()
        self.poll_out_tab, self.poll_out_layout = self._create_scrollable_tab()
        self.explicit_tab, self.explicit_layout = self._create_scrollable_tab()
        
        self.tab_widget.addTab(self.poll_in_tab, "Poll-In (RX)")
        self.tab_widget.addTab(self.poll_out_tab, "Poll-Out (TX)")
        self.tab_widget.addTab(self.explicit_tab, "Explicit")

    def _create_scrollable_tab(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        container = QWidget()
        # 개별 위젯들이 세로로 차곡차곡 쌓이도록 QVBoxLayout 사용
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2) # 위젯 간 간격 좁게
        layout.setAlignment(Qt.AlignTop) # 위에서부터 정렬
        
        scroll_area.setWidget(container) 
        return scroll_area, layout

    def __build_ui(self, schema_path):
        if schema_path is None:
            self.lbl_name.setText("이름 : DNET 장치")
            self.current_schema_path = None
            self._clear_layout(self.poll_in_layout)
            self._clear_layout(self.poll_out_layout)
            self._clear_layout(self.explicit_layout)
            return

        model : DnetModel = DnetModel()
        model.load_from_json(schema_path)   
        self.current_schema_path = schema_path

        file_name = Path(schema_path).name
        self.lbl_name.setText(f"이름 : {file_name}")
        
        self._clear_layout(self.poll_in_layout)
        self._clear_layout(self.poll_out_layout)
        self._clear_layout(self.explicit_layout)

        # 1. Poll-In 위젯 렌더링 및 시그널 연결
        curr_offset : int = 0
        for item in model.poll_in_items:
            widget = ItemWidget(item, ItemType.PollIn)
            # 시그널 연결
            widget.sig_enable_changed.connect(self.on_enable_changed)
            widget.sig_move_up.connect(self.on_move_up)
            widget.sig_move_down.connect(self.on_move_down)
            widget.sig_delete.connect(self.on_delete)
            widget.sig_edit.connect(self.on_edit)    

            widget.set_offset(curr_offset)
            curr_offset += widget.size

            self.poll_in_layout.addWidget(widget)
            

        btn_add_pollin = CustomPushButton("+ Poll-In 아이템 추가")
        btn_add_pollin.setMinimumHeight(40) # 버튼을 누르기 쉽게 높이를 조금 키움
        self.poll_in_layout.addWidget(btn_add_pollin)  
        btn_add_pollin.clicked.connect(self.on_pollin_add)

        # 2. Poll-Out 위젯 렌더링 및 시그널 연결
        curr_offset = 0
        for item in model.poll_out_items:
            widget = ItemWidget(item, ItemType.PollOut)
            # 시그널 연결
            widget.sig_enable_changed.connect(self.on_enable_changed)
            widget.sig_move_up.connect(self.on_move_up)
            widget.sig_move_down.connect(self.on_move_down)
            widget.sig_delete.connect(self.on_delete)
            widget.sig_edit.connect(self.on_edit)    

            widget.set_offset(curr_offset)
            curr_offset += widget.size
            
            self.poll_out_layout.addWidget(widget)

        btn_add_pollout = CustomPushButton("+ Poll-Out 아이템 추가")
        btn_add_pollout.setMinimumHeight(40) # 버튼을 누르기 쉽게 높이를 조금 키움
        self.poll_out_layout.addWidget(btn_add_pollout)  
        btn_add_pollout.clicked.connect(self.on_pollout_add)
             

        # 3. Explicit 위젯 렌더링 및 시그널 연결
        for item in model.explicit_messages:
            widget = ItemWidget(item, ItemType.Explicit)
            
            # 시그널 연결
            widget.sig_delete.connect(self.on_delete)
            widget.sig_edit.connect(self.on_edit)
            widget.sig_req_write_explicit.connect(self.on_req_write_explicit)
            widget.sig_req_read_explicit.connect(self.on_req_read_explicit)  
            widget.sig_req_execute_explicit.connect(self.on_req_execute_explicit)
            
            self.explicit_layout.addWidget(widget)

        btn_add_explicit = CustomPushButton("+ Explicit 아이템 추가")
        btn_add_explicit.setMinimumHeight(40) # 버튼을 누르기 쉽게 높이를 조금 키움
        self.explicit_layout.addWidget(btn_add_explicit)   
        btn_add_explicit.clicked.connect(self.on_explicit_add)

    def _clear_layout(self, layout: QFormLayout):
        """레이아웃 내부의 모든 아이템을 제거합니다."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def on_enable_changed(self, widget: ItemWidget):
        self._update_all_offsets(widget.parent().layout())

    def on_pollin_add(self):
        emptyItem = CyclicItem(
            name="New Item",
            type=DataType.UINT8,
            ui_type=UiType.NUMBER,
            enum_list=[],
            bitmap=[],
            is_json_parsing_err=False
        )

        widget = ItemWidget(emptyItem, ItemType.PollIn)
        # 시그널 연결
        widget.sig_enable_changed.connect(self.on_enable_changed)
        widget.sig_move_up.connect(self.on_move_up)
        widget.sig_move_down.connect(self.on_move_down)
        widget.sig_delete.connect(self.on_delete)
        widget.sig_edit.connect(self.on_edit)    
        widget.set_offset(0)
        self.poll_in_layout.insertWidget(self.poll_in_layout.count() - 1, widget)

        dialog = ItemEditDialog(widget, self)
        if dialog.exec() == QDialog.Rejected:
            self.poll_in_layout.removeWidget(widget)
            widget.deleteLater()

    def on_pollout_add(self):
        emptyItem = CyclicItem(
            name="New Item",
            type=DataType.UINT8,
            ui_type=UiType.NUMBER,
            enum_list=[],
            bitmap=[],
            is_json_parsing_err=False
        )

        widget = ItemWidget(emptyItem, ItemType.PollOut)
        # 시그널 연결
        widget.sig_enable_changed.connect(self.on_enable_changed)
        widget.sig_move_up.connect(self.on_move_up)
        widget.sig_move_down.connect(self.on_move_down)
        widget.sig_delete.connect(self.on_delete)
        widget.sig_edit.connect(self.on_edit)    
        widget.set_offset(0)
        self.poll_out_layout.insertWidget(self.poll_out_layout.count() - 1, widget)

        dialog = ItemEditDialog(widget, self)
        if dialog.exec() == QDialog.Rejected:
            self.poll_out_layout.removeWidget(widget)
            widget.deleteLater()

    def on_explicit_add(self):
        emptyItem = ExplicitItem(
            name="New Item",
            type=DataType.UINT8,
            ui_type=UiType.NUMBER,
            enum_list=[],
            bitmap=[],
            service_code = 0,
            class_id = 1,
            instance_id = 1,
            attribute_id = 1,
            access_type = AccessType.RW,
            is_json_parsing_err=False
        )

        widget = ItemWidget(emptyItem, ItemType.Explicit)
        # 시그널 연결
        widget.sig_enable_changed.connect(self.on_enable_changed)
        widget.sig_move_up.connect(self.on_move_up)
        widget.sig_move_down.connect(self.on_move_down)
        widget.sig_delete.connect(self.on_delete)
        widget.sig_edit.connect(self.on_edit)    
        widget.set_offset(0)
        self.explicit_layout.insertWidget(self.explicit_layout.count() - 1, widget)

        dialog = ItemEditDialog(widget, self)
        if dialog.exec() == QDialog.Rejected:
            self.explicit_layout.removeWidget(widget)
            widget.deleteLater()

    def on_edit(self, widget: ItemWidget):
        dialog = ItemEditDialog(widget, self)
        dialog.exec()

    def on_delete(self, widget: ItemWidget):
        layout = widget.parent().layout()
        
        # 아이템 제거
        layout.removeWidget(widget)
        widget.deleteLater()
        
        # 삭제 후 offset 재계산
        self._update_all_offsets(layout)

    def on_move_up(self, widget: ItemWidget):
        layout = widget.parent().layout()
        index = layout.indexOf(widget)
        
        # 첫 번째 아이템이 아니면 위로 이동 가능
        if index > 0:
            layout.removeWidget(widget)
            layout.insertWidget(index - 1, widget)
            self._update_all_offsets(layout)
        
    def on_move_down(self, widget: ItemWidget):
        layout = widget.parent().layout()
        index = layout.indexOf(widget)
        
        # 마지막 아이템(추가 버튼 제외)보다 위일 때만 아래로 이동 가능
        # layout.count() - 1은 '아이템 추가' 버튼이므로, index < layout.count() - 2 조건 사용
        if index < layout.count() - 2:
            layout.removeWidget(widget)
            layout.insertWidget(index + 1, widget)
            self._update_all_offsets(layout)

    def on_req_write_explicit(self, class_id: int, instance_id: int, attribute_id: int, data: bytes):
        self.sig_req_explicit.emit(16, class_id, instance_id, attribute_id, data)

    def on_req_read_explicit(self, class_id: int, instance_id: int, attribute_id: int):
        self.sig_req_explicit.emit(14,class_id, instance_id, attribute_id, None)

    def on_req_execute_explicit(self, service_code: int, class_id: int, instance_id: int, attribute_id: int):
        self.sig_req_explicit.emit(service_code, class_id, instance_id, attribute_id, None)

    def _update_all_offsets(self, layout):
        """레이아웃 내의 모든 ItemWidget의 Offset을 재계산합니다."""
        curr_offset = 0
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            
            # ItemWidget인 경우만 Offset 업데이트 (추가 버튼 등 제외)
            if isinstance(widget, ItemWidget):
                if widget.chk_enabled:
                    widget.set_offset(curr_offset)
                    curr_offset += widget.size
        
        