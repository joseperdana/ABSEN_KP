import face_recognition
import cv2

image_bgr = cv2.imread("test.jpg")  # Ganti dengan nama file gambar kamu
image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

print("Type:", type(image_rgb))
print("Shape:", image_rgb.shape)
print("Dtype:", image_rgb.dtype)

face_locations = face_recognition.face_locations(image_rgb)
print("Jumlah wajah:", len(face_locations))
