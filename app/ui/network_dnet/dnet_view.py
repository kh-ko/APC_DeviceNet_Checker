from app.ui.network_view import NetworkView

class DnetView(NetworkView):
    """
    DnetModel의 데이터를 읽어와 Poll-In, Poll-Out, Explicit 메시지를 
    탭 형태로 보여주는 커스텀 위젯입니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def shutdown(self):
        pass

    def create_new_schema(self):
        pass

    def load_schema(self):
        pass

    def save_schema(self):
        pass

    def save_as_schema(self):
        pass

    def remove_schema(self):
        pass