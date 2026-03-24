from pathlib import Path  # 파일 맨 위쪽 import 영역에 추가
from model.dnet.dnet_item_model import PollInItem, PollOutItem, ExplicitItem
from model.dnet.dnet_item_model import EnumItem
from model.dnet.dnet_item_model import BitmapItem
from view.components.dnet.pollin_item_edit_dialog import PollInItemEditDialog
from view.components.dnet.pollout_item_edit_dialog import PollOutItemEditDialog
from view.components.dnet.explicit_item_edit_dialog import ExplicitItemEditDialog
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QScrollArea, QFormLayout, 
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QHBoxLayout, QDialog
)
from PySide6.QtCore import Qt

from model.dnet.dnet_model import DnetModel
from model.dnet.dnet_item_model import BaseDnetItem
from view.components.dnet.pollin_item_widget import PollInItemWidget
from view.components.dnet.pollout_item_widget import PollOutItemWidget
from view.components.dnet.explicit_item_widget import ExplicitItemWidget


class DnetWidget(QWidget):
    """
    DnetModel의 데이터를 읽어와 Poll-In, Poll-Out, Explicit 메시지를 
    탭 형태로 보여주는 커스텀 위젯입니다.
    """
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        
        # 싱글톤 DnetModel 인스턴스 가져오기
        self.dnet_model = DnetModel()
        self.dnet_model.load_from_json(path)
        
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- 상단 컨트롤 패널 추가 ---
        self.top_control_layout = QHBoxLayout()
        self.top_control_layout.setContentsMargins(5, 5, 5, 5)
        self.top_control_layout.setSpacing(10)

        # 1. 이름 라벨
        # 모델에 이름 속성이 있다면 self.dnet_model.name 등으로 변경 가능합니다.
        self.lbl_name = QLabel("이름 : DNET 장치") 
        self.top_control_layout.addWidget(self.lbl_name)
        
        # 2. 사이클 주기 입력 (ms)
        self.top_control_layout.addWidget(QLabel("사이클 주기:"))
        self.spin_cycle = QSpinBox()
        self.spin_cycle.setRange(1, 10000) # 1ms ~ 10000ms 범위 설정
        self.spin_cycle.setValue(100)      # 기본값 100ms
        self.spin_cycle.setSuffix(" ms")   # 숫자 뒤에 'ms' 텍스트 표시
        self.top_control_layout.addWidget(self.spin_cycle)
        
        # 3. Polling 시작 버튼
        self.btn_start_polling = QPushButton("Polling 시작")
        self.top_control_layout.addWidget(self.btn_start_polling)
        
        # 4. Polling 중지 버튼
        self.btn_stop_polling = QPushButton("Polling 중지")
        self.top_control_layout.addWidget(self.btn_stop_polling)
        
        # 5. Out 데이터 쓰기 버튼
        self.btn_write_out = QPushButton("Out 데이터 쓰기")
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

    def update_ui(self):
        """모델 데이터를 기반으로 전체 리스트를 다시 그립니다."""
        file_name = Path(self.dnet_model.schema_path).name
        self.lbl_name.setText(f"이름 : {file_name}")
        
        self._clear_layout(self.poll_in_layout)
        self._clear_layout(self.poll_out_layout)
        self._clear_layout(self.explicit_layout)

        # 1. Poll-In 위젯 렌더링 및 시그널 연결
        for item in self.dnet_model.poll_in_items:
            widget = PollInItemWidget(item)
            
            # 시그널 연결
            widget.sig_move_up.connect(self.on_pollin_move_up)
            widget.sig_move_down.connect(self.on_pollin_move_down)
            widget.sig_delete.connect(self.on_pollin_delete)
            widget.sig_edit.connect(self.on_pollin_edit)
            widget.sig_enable_changed.connect(self.on_pollin_enable_changed)
            
            self.poll_in_layout.addWidget(widget)

        btn_add_pollin = QPushButton("+ Poll-In 아이템 추가")
        btn_add_pollin.setMinimumHeight(40) # 버튼을 누르기 쉽게 높이를 조금 키움
        btn_add_pollin.clicked.connect(self.on_pollin_add)
        self.poll_in_layout.addWidget(btn_add_pollin)

        # 2. Poll-Out 위젯 렌더링 및 시그널 연결
        for item in self.dnet_model.poll_out_items:
            widget = PollOutItemWidget(item)
            
            # 시그널 연결
            widget.sig_move_up.connect(self.on_pollout_move_up)
            widget.sig_move_down.connect(self.on_pollout_move_down)
            widget.sig_delete.connect(self.on_pollout_delete)
            widget.sig_edit.connect(self.on_pollout_edit)
            widget.sig_enable_changed.connect(self.on_pollout_enable_changed)
            
            self.poll_out_layout.addWidget(widget)

        btn_add_pollout = QPushButton("+ Poll-Out 아이템 추가")
        btn_add_pollout.setMinimumHeight(40) # 버튼을 누르기 쉽게 높이를 조금 키움
        btn_add_pollout.clicked.connect(self.on_pollout_add)
        self.poll_out_layout.addWidget(btn_add_pollout)       

        # 3. Explicit 위젯 렌더링 및 시그널 연결
        for item in self.dnet_model.explicit_messages:
            widget = ExplicitItemWidget(item)
            
            # 시그널 연결
            widget.sig_delete.connect(self.on_explicit_delete)
            widget.sig_edit.connect(self.on_explicit_edit)
            widget.sig_req_explicit.connect(self.on_explicit_req_explicit)
            
            self.explicit_layout.addWidget(widget)

        btn_add_explicit = QPushButton("+ Explicit 아이템 추가")
        btn_add_explicit.setMinimumHeight(40) # 버튼을 누르기 쉽게 높이를 조금 키움
        btn_add_explicit.clicked.connect(self.on_explicit_add)
        self.explicit_layout.addWidget(btn_add_explicit)   

    def _clear_layout(self, layout: QFormLayout):
        """레이아웃 내부의 모든 아이템을 제거합니다."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def on_pollin_add(self):
        new_item = PollInItem()
        new_item.name = "New Item"
        new_item.type = "uint8"
        new_item.ui_type = "number"
        new_item.validate_and_calculate_size()
        self.dnet_model.poll_in_items.append(new_item)
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_pollin_move_up(self, widget: PollInItemWidget):
        try:
            current_index = self.dnet_model.poll_in_items.index(widget.item)
        except ValueError:
            return
            
        if current_index <= 0:
            return
            
        items = self.dnet_model.poll_in_items
        items[current_index - 1], items[current_index] = items[current_index], items[current_index - 1]
        
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_pollin_move_down(self, widget: PollInItemWidget):
        try:
            current_index = self.dnet_model.poll_in_items.index(widget.item)
        except ValueError:
            return
            
        if current_index >= len(self.dnet_model.poll_in_items) - 1:
            return
            
        items = self.dnet_model.poll_in_items
        items[current_index + 1], items[current_index] = items[current_index], items[current_index + 1]
        
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_pollin_delete(self, widget: PollInItemWidget):
        try:
            current_index = self.dnet_model.poll_in_items.index(widget.item)
        except ValueError:
            return
            
        self.dnet_model.poll_in_items.pop(current_index)
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_pollin_edit(self, widget: PollInItemWidget):
        dialog = PollInItemEditDialog(widget.item, self)
        
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_updated_data()
            
            # 1. 텍스트/콤보박스로 입력된 기본 속성 변경
            widget.item.name = new_data.get("name", "")
            widget.item.type = new_data.get("type", "")
            widget.item.ui_type = new_data.get("ui_type", "")
            
            # 2. Table 기반의 리스트 속성 업데이트
            if "enum_list" in new_data:
                widget.item.enum_list = [EnumItem(**e) for e in new_data["enum_list"]]
            else:
                widget.item.enum_list = None
                
            if "bitmap" in new_data:
                widget.item.bitmap = [BitmapItem(**b) for b in new_data["bitmap"]]
            else:
                widget.item.bitmap = None
            
            # 3. size, json_parsing_err 등 데이터 모델 단에서 재계산 (Pydantic validator 직접 트리거)
            widget.item.validate_and_calculate_size()
            
            # 4. Offset 재계산 (전체 리스트)
            self.dnet_model.calculate_offset()
            
            # 5. UI 새로 그리기
            self.update_ui()

    def on_pollin_enable_changed(self, widget: PollInItemWidget, is_enabled: bool):
        self.dnet_model.calculate_offset()     
        self.update_ui() 

    
    def on_pollout_add(self):
        new_item = PollOutItem()
        new_item.name = "New Item"
        new_item.type = "uint8"
        new_item.ui_type = "number"
        new_item.validate_and_calculate_size()
        self.dnet_model.poll_out_items.append(new_item)
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_pollout_move_up(self, widget: PollOutItemWidget):
        try:
            current_index = self.dnet_model.poll_out_items.index(widget.item)
        except ValueError:
            return
            
        if current_index <= 0:
            return
            
        items = self.dnet_model.poll_out_items
        items[current_index - 1], items[current_index] = items[current_index], items[current_index - 1]
        
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_pollout_move_down(self, widget: PollOutItemWidget):
        try:
            current_index = self.dnet_model.poll_out_items.index(widget.item)
        except ValueError:
            return
            
        if current_index >= len(self.dnet_model.poll_out_items) - 1:
            return
            
        items = self.dnet_model.poll_out_items
        items[current_index + 1], items[current_index] = items[current_index], items[current_index + 1]
        
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_pollout_delete(self, widget: PollOutItemWidget):
        try:
            current_index = self.dnet_model.poll_out_items.index(widget.item)
        except ValueError:
            return
            
        self.dnet_model.poll_out_items.pop(current_index)
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_pollout_edit(self, widget: PollOutItemWidget):
        dialog = PollOutItemEditDialog(widget.item, self)
        
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_updated_data()
            
            # 1. 텍스트/콤보박스로 입력된 기본 속성 변경
            widget.item.name = new_data.get("name", "")
            widget.item.type = new_data.get("type", "")
            widget.item.ui_type = new_data.get("ui_type", "")
            
            # 2. Table 기반의 리스트 속성 업데이트
            if "enum_list" in new_data:
                widget.item.enum_list = [EnumItem(**e) for e in new_data["enum_list"]]
            else:
                widget.item.enum_list = None
            
            # 3. size, json_parsing_err 등 데이터 모델 단에서 재계산 (Pydantic validator 직접 트리거)
            widget.item.validate_and_calculate_size()
            
            # 4. Offset 재계산 (전체 리스트)
            self.dnet_model.calculate_offset()
            
            # 5. UI 새로 그리기
            self.update_ui()

    def on_pollout_enable_changed(self, widget: PollOutItemWidget, is_enabled: bool):
        self.dnet_model.calculate_offset()       
        self.update_ui()     

    def on_explicit_add(self):
        new_item = ExplicitItem()
        new_item.name = "New Item"
        new_item.class_id = 0
        new_item.instance_id = 0
        new_item.attribute_id = 0
        new_item.access_type = "RW"
        new_item.type = "uint8"
        new_item.ui_type = "number"
        new_item.validate_and_calculate_size()
        self.dnet_model.explicit_messages.append(new_item)
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_explicit_delete(self, widget: ExplicitItemWidget):
        try:
            current_index = self.dnet_model.explicit_messages.index(widget.item)
        except ValueError:
            return
            
        self.dnet_model.explicit_messages.pop(current_index)
        self.dnet_model.calculate_offset()
        self.update_ui()

    def on_explicit_edit(self, widget: ExplicitItemWidget):
        dialog = ExplicitItemEditDialog(widget.item, self)
        
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_updated_data()
            
            # 1. 텍스트/콤보박스로 입력된 기본 속성 변경
            widget.item.name = new_data.get("name", "")
            widget.item.class_id = new_data.get("class_id", 0)
            widget.item.instance_id = new_data.get("instance_id", 0)
            widget.item.attribute_id = new_data.get("attribute_id", 0)
            widget.item.access_type = new_data.get("access_type", "")
            widget.item.type = new_data.get("type", "")
            widget.item.ui_type = new_data.get("ui_type", "")
            
            # 2. Table 기반의 리스트 속성 업데이트
            if "enum_list" in new_data:
                widget.item.enum_list = [EnumItem(**e) for e in new_data["enum_list"]]
            else:
                widget.item.enum_list = None
                
            if "bitmap" in new_data:
                widget.item.bitmap = [BitmapItem(**b) for b in new_data["bitmap"]]
            else:
                widget.item.bitmap = None
            
            # 3. size, json_parsing_err 등 데이터 모델 단에서 재계산 (Pydantic validator 직접 트리거)
            widget.item.validate_and_calculate_size()
            
            # 4. Offset 재계산 (전체 리스트)
            self.dnet_model.calculate_offset()
            
            # 5. UI 새로 그리기
            self.update_ui()

    def on_explicit_req_explicit(self, svc_code:int, class_id:int, instance_id:int, attribute_id:int, payload:bytes):
        print(f"Explicit Request: {svc_code}, {class_id}, {instance_id}, {attribute_id}, {payload.hex(' ')}")
