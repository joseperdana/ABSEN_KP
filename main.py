import os.path
import datetime
import pickle
import numpy as np
import tkinter as tk
import cv2
from PIL import Image, ImageTk
import face_recognition

import util


class App:
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.geometry("1200x520+350+100")

        self.login_button_main_window = util.get_button(self.main_window, 'login', 'green', self.login)
        self.login_button_main_window.place(x=750, y=200)

        self.logout_button_main_window = util.get_button(self.main_window, 'logout', 'red', self.logout)
        self.logout_button_main_window.place(x=750, y=300)

        self.register_new_user_button_main_window = util.get_button(self.main_window, 'register new user', 'gray',
                                                                    self.register_new_user, fg='black')
        self.register_new_user_button_main_window.place(x=750, y=400)

        self.webcam_label = util.get_img_label(self.main_window)
        self.webcam_label.place(x=10, y=0, width=700, height=500)

        self.add_webcam(self.webcam_label)

        self.db_dir = './db'
        if not os.path.exists(self.db_dir):
            os.mkdir(self.db_dir)

        self.log_path = './log.txt'

    def add_webcam(self, label):
        if 'cap' not in self.__dict__:
            self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
          util.msg.box('Error', 'Failed to open webcam.')
          return
        self._label = label
        self.process_webcam()

    def process_webcam(self):
        ret, frame = self.cap.read()

        if not ret or frame is None:
          print("Warning: Failed to capture image from webcam.")
          self._label.after(1000, self.process_webcam)
          return
        
        self.most_recent_capture_arr = frame
        img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
        self.most_recent_capture_pil = Image.fromarray(img_)
        imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
        self._label.imgtk = imgtk
        self._label.configure(image=imgtk)

        self._label.after(20, self.process_webcam)

    def login(self):
        name = util.recognize(self.most_recent_capture_arr, self.db_dir, tolerance=0.5)

        if name in ['unknown_person', 'no_persons_found']:
            util.msg_box('Ups...', 'Unknown user. Please register new user or try again.')
        else:
            util.msg_box('Welcome back !', f'Welcome, {name}.')
            with open(self.log_path, 'a') as f:
                f.write(f'{name},{datetime.datetime.now()},in\n')

    def logout(self):
        name = util.recognize(self.most_recent_capture_arr, self.db_dir,tolerance=0.5)

        if name in ['unknown_person', 'no_persons_found']:
            util.msg_box('Ups...', 'Unknown user. Please register new user or try again.')
        else:
            util.msg_box('Hasta la vista !', f'Goodbye, {name}.')
            with open(self.log_path, 'a') as f:
                f.write(f'{name},{datetime.datetime.now()},out\n')

    def register_new_user(self):
        self.register_new_user_window = tk.Toplevel(self.main_window)
        self.register_new_user_window.geometry("1200x520+370+120")

        self.accept_button_register_new_user_window = util.get_button(self.register_new_user_window, 'Accept', 'green', self.accept_register_new_user)
        self.accept_button_register_new_user_window.place(x=750, y=300)

        self.try_again_button_register_new_user_window = util.get_button(self.register_new_user_window, 'Try again', 'red', self.try_again_register_new_user)
        self.try_again_button_register_new_user_window.place(x=750, y=400)

        self.capture_label = util.get_img_label(self.register_new_user_window)
        self.capture_label.place(x=10, y=0, width=700, height=500)

        self.add_img_to_label(self.capture_label)

        self.entry_text_register_new_user = util.get_entry_text(self.register_new_user_window)
        self.entry_text_register_new_user.place(x=750, y=150)

        self.text_label_register_new_user = util.get_text_label(self.register_new_user_window, 'Please, \ninput username:')
        self.text_label_register_new_user.place(x=750, y=70)

    def try_again_register_new_user(self):
        self.register_new_user_window.destroy()

    def add_img_to_label(self, label):
        ret, frame = self.cap.read()

        if not ret or frame is None or frame.size==0:
            util.msg_box('Error', 'Failed to capture image from webcam.')
            return

        self.register_new_user_capture = frame.copy()
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        imgtk = ImageTk.PhotoImage(image=pil_img)
        label.imgtk = imgtk
        label.configure(image=imgtk)

    def start(self):
        self.main_window.mainloop()

    def accept_register_new_user(self):
        name = self.entry_text_register_new_user.get(1.0, "end-1c").strip()

        # Step 1: Validate input image
        if self.register_new_user_capture is None:
            util.msg_box('Error', 'No image captured. Please try again.')
            return

        # Step 2: Convert BGR to RGB
        try:
            rgb_image = cv2.cvtColor(self.register_new_user_capture, cv2.COLOR_BGR2RGB)
        except Exception as e:
            util.msg_box('Error', f'OpenCV conversion failed: {e}')
            return

        # Step 3: Confirm dtype and shape
        if rgb_image.dtype != np.uint8:
            rgb_image = rgb_image.astype(np.uint8)

        if len(rgb_image.shape) != 3 or rgb_image.shape[2] != 3:
            util.msg_box('Error', 'Image must be 3-channel RGB.')
            return
        print(f"Dtype: {rgb_image.dtype}")
        print(f"Shape: {rgb_image.shape}")
        print(f"Min: {rgb_image.min()}, Max: {rgb_image.max()}")
        # Step 4: Call face_recognition
        try:
            print("Type:", type(rgb_image))
            print("Dtype:", rgb_image.dtype)
            print("Shape:", rgb_image.shape)
            print("Min:", np.min(rgb_image), "Max:", np.max(rgb_image))

            face_locations = face_recognition.face_locations(rgb_image)

            if not face_locations:
                util.msg_box('Error', 'No face detected in the image. Please try again with a clearer face.')
                return

            encodings = face_recognition.face_encodings(rgb_image, known_face_locations=face_locations)

            if not encodings:
                util.msg_box('Error', 'Face encoding failed. Try with a better lighting and clear face.')
                return

        except Exception as e:
            util.msg_box('Error', f'Face recognition failed: {e}')
            return

        embeddings = encodings[0]

        # Save embedding to file
        with open(os.path.join(self.db_dir, f'{name}.pickle'), 'wb') as file:
            pickle.dump(embeddings, file)

        util.msg_box('Success!', 'User was registered successfully!')
        self.register_new_user_window.destroy()


if __name__ == "__main__":
    app = App()
    app.start()
