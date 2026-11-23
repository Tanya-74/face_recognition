from sklearn.datasets import fetch_lfw_people

# Ye internet se ek baar download karega (setup ke time allowed hai)
lfw = fetch_lfw_people(min_faces_per_person=2, color=True, resize=1.0)

print("Total photos:", len(lfw.images))
print("Total labels:", len(lfw.target_names))