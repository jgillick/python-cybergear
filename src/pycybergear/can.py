class CyberMotorMessage:
    arbitration_id: int
    data: bytearray
    is_extended_id: bool = True

    def __init__(self, arbitration_id, data):
        self.arbitration_id = arbitration_id
        self.data = data
