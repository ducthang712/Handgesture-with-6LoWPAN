import cv2
import mediapipe as mp
import time

# ------------------------HAND GESTURE CONFIGURATION ---------------------#
# Khởi tạo Mediapipe
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# Tạo đối tượng nhận diện bàn tay
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)

# Danh sách các ID của đầu ngón tay
finger_tips = [4, 8, 12, 16, 20]

# Mở camera
cap = cv2.VideoCapture(0)

# Thiết lập độ phân giải
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# Biến lưu thời gian bắt đầu và trạng thái trước đó
condition_start_time = 0
previous_condition = ""
status_message = "Wait"
duplicate_message = ""
last_sent_command = ""
status_start_time = 0

# mới thêm vào
behind_done = ""
message_reply = ""
display_start_time = None
# --------------------------NETWORK CONFIGURATION------------------------------#
import socket
import json

# VM_IP = "192.168.1.17"
# port_sending = 5000

VM_IP = input("Enter Contiki Host IP: ")
port_sending = input ("Choose forwarding port: ")
# -----------------------------------------------------------------------------#
def message_sending_to_VM(message, host, port):
    error = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Connect to the VM
        sock.connect((host, port))
        print(f"Connected to {host}:{port}")

        # Send the message
        sock.sendall(json.dumps(message).encode())
        print("Message sent!")

        sock.settimeout(3)

    except socket.timeout:
        print("Timeout message sending to VM")
        error = "time_out"
    except Exception as e:
        print("Error: {}".format(e))
        error = "error"
    finally:
        sock.close()
        return error


def message_listening_to_VM(host, port):
    error = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.listen(1)
        print("Server is listening on {}:{}".format(host, port))

        # Wait for a connection
        conn, addr = sock.accept()
        print("Connected by {}".format(addr))

        sock.settimeout(3)

        # Receive the message
        data = conn.recv(1024).decode()
        print("Received: {}".format(data))

        conn.close()
    except socket.timeout:
        print("Timeout message listening to VM")
        error = "time_out"
    except Exception as e:
        print("Error: {}".format(e))
        error = "error"
    finally:
        sock.close()
        return data, error


def cooja_controller(node_ip, command):
    mess_json = {"node": f"{node_ip}", "command": f"{command}"}
    error_send = message_sending_to_VM(mess_json, VM_IP, port_sending)
    if error_send == None:
        message_reply, error_listen = message_listening_to_VM("0.0.0.0", port_sending)
        if error_listen == "error":
            message_reply = "Listening message failed. Check connection."
    else:
        message_reply = "Sending message failed. Check connection."
    return message_reply

if __name__ == "__main__":
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Chuyển đổi BGR sang RGB (Yêu cầu của Mediapipe)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb_frame)

        # Kiểm tra số lượng tay phát hiện được
        if not result.multi_hand_landmarks or len(result.multi_hand_landmarks) < 2:
            # Nếu không đủ 2 tay, hiển thị trạng thái "Wait"
            status_message = "Wait"
            cv2.putText(frame, f"please put your hand up", (250, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
            cv2.putText(frame, last_sent_command, (frame.shape[1] // 4, frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Hand Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue  # Bỏ qua xử lý logic bên dưới

        # Khởi tạo số ngón tay đếm được cho từng tay
        left_hand_fingers = 0
        right_hand_fingers = 0
        current_condition = ""

        for hand_landmarks, hand_classification in zip(result.multi_hand_landmarks, result.multi_handedness):
            # Lấy nhãn tay từ Mediapipe và đảo ngược
            label = hand_classification.classification[0].label
            if label == "Left":
                label = "Right"  # Đổi ngược
            else:
                label = "Left"  # Đổi ngược

            # Vẽ landmarks lên khung hình
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Lấy danh sách vị trí landmarks
            lm_list = []
            h, w, c = frame.shape
            for id, lm in enumerate(hand_landmarks.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append((cx, cy))

            # Đếm số ngón tay
            if lm_list:
                fingers = []

                # Ngón cái
                if label == "Left":  # Tay trái
                    if lm_list[finger_tips[0]][0] < lm_list[finger_tips[0] - 1][0]:
                        fingers.append(1)
                    else:
                        fingers.append(0)
                elif label == "Right":  # Tay phải
                    if lm_list[finger_tips[0]][0] > lm_list[finger_tips[0] - 1][0]:
                        fingers.append(1)
                    else:
                        fingers.append(0)

                # Các ngón còn lại
                for tip_id in finger_tips[1:]:
                    if lm_list[tip_id][1] < lm_list[tip_id - 2][1]:  # Kiểm tra theo trục Y
                        fingers.append(1)
                    else:
                        fingers.append(0)

                # Tổng số ngón tay mở
                finger_count = fingers.count(1)

                # Phân biệt tay trái và tay phải
                if label == "Left":
                    left_hand_fingers = finger_count
                elif label == "Right":
                    right_hand_fingers = finger_count

        # Các thao tác theo logic mới
        node = "all" if left_hand_fingers == 0 else str(left_hand_fingers)
        command_map = {
            0: "led_off",
            1: "led_on",
            2: "get_led_status",
            3: "get_temp_status",
            4: "get_led_status",
            5: "led_dim"
        }
        command = command_map.get(right_hand_fingers, "invalid")

        if node != "all" or command != "invalid":
            current_condition = f'{{node: "{node}" , command: "{command}"}}'
            # current_condition= {"node": f"{node}", "command": f"{command}"}

        # Kiểm tra nếu điều kiện hiện tại giữ nguyên trong 3 giây
        if current_condition != "" and current_condition == previous_condition:
            if time.time() - condition_start_time >= 3:
                # Kiểm tra nếu lệnh đã gửi trước đó
                if current_condition == last_sent_command:
                    duplicate_message = "packet transmitted"
                    status_message = "Wait"  # Không thay đổi trạng thái nếu lệnh trùng
                else:
                    # Hiển thị trạng thái gửi lệnh
                    status_message = "Sending"
                    print(status_message)  # In ra trạng thái "Sending"
                    cv2.putText(frame, "Sending....", (500, 600), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 3)
                    cv2.imshow("Hand Tracking", frame)
                    cv2.waitKey(1)  # Cập nhật khung hình ngay lập tức trong khi đang gửi lệnh
                    cv2.putText(frame, current_condition, (frame.shape[1] // 4, frame.shape[0] - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                    print(current_condition)  # In ra console
                    message_reply = cooja_controller(node, command)

                    # Giả lập việc gửi lệnh thành công hoặc thất bại
                    success = True  # Hoặc logic thực tế
                    if success:
                        status_message = "Done"
                        last_sent_command = current_condition
                        behind_done = message_reply

                    else:
                        status_message = "Fail"
                    print(status_message)  # In ra trạng thái "Done" hoặc "Fail"
                status_start_time = time.time()
        else:
            condition_start_time = time.time()  # Reset thời gian nếu điều kiện thay đổi
            duplicate_message = ""  # Xóa thông báo "Lệnh này đã gửi rồi"

        # Hiển thị trạng thái cuối cùng lên màn hình
        cv2.putText(frame, f"Message: {status_message}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        cv2.putText(frame, last_sent_command, (frame.shape[1] // 4, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # hien thi sau done
        if behind_done == message_reply and display_start_time is None:
            display_start_time = time.time()
        if display_start_time is not None:
            if time.time() - display_start_time <= 5:
                cv2.putText(frame, behind_done, (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            else:
                display_start_time = None
                behind_done = ""

        # Nếu không có gì giữ nguyên 3 giây, trạng thái là "Wait"
        if time.time() - status_start_time > 3:
            status_message = "Wait"

        # Hiển thị thông báo "Lệnh này đã gửi rồi"
        cv2.putText(frame, duplicate_message, (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        # print(status_message)  # In ra trạng thái hiện tại

        # Cập nhật điều kiện trước đó
        previous_condition = current_condition

        # Hiển thị khung hình
        cv2.putText(frame, f"Tay trai: {left_hand_fingers}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"Tay phai: {right_hand_fingers}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Hand Tracking", frame)

        # Thoát nếu nhấn phím 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
