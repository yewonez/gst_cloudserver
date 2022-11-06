from RequestAPI.requestAPI import *
from StreamAPI.rtsp_stream import *
from StreamAPI.rtsp_image import *
import os
import cv2

def print_api_list():
  print("############## Cloud Client -> Edge Server ##############")
  print("Function List")
  print("1. start stream")
  print("2. get snap shot()")
  print("0. exit demo")


if __name__ == "__main__":
    print_api_list()
    test_rtspsrc = "rtsp://127.0.0.1:3002/"
    edgeID = 0

    while True:
        user_input = int(
            input(
                "Select an API to call (1 to 2). You can press 9 to see the API List: "
            ))

        if user_input == 1:
            print("### start stream ###")

            test123 = Gstreamer_thread1(test_rtspsrc + "test")
            test123.start()
            time.sleep(10)  # 종료조건은 일단, 10초 후 종료한다고 가정
            test123.terminate_thread()
            test123.join()

        if user_input == 2:
            print("### get snap shot ###")
            test123 = Gstreamer_thread2(test_rtspsrc + "test")
            test123.start()
            time.sleep(5)
            temp = test123.get_snapshot()
            time.sleep(10)  # 종료조건은 일단, 10초 후 종료한다고 가정
            test123.terminate_thread()
            test123.join()

            cv2.imwrite("test.jpeg", temp)


        if user_input == 0:
            break

