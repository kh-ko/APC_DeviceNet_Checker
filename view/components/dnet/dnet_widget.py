from model.dnet.dnet_item_model import PollInItem
from model.dnet.dnet_item_model import EnumItem
from model.dnet.dnet_item_model import BitmapItem
from view.components.dnet.pollin_item_edit_dialog import PollInItemEditDialog
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QScrollArea, QFormLayout, 
    QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QHBoxLayout, QDialog
)
from PySide6.QtCore import Qt

from model.dnet.dnet_model import DnetModel
from model.dnet.dnet_item_model import BaseDnetItem
from view.components.dnet.pollin_item_widget import PollInItemWidget


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
