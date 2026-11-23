from sklearn.datasets import fetch_lfw_people

# Downloads from the internet once (allowed during setup)
lfw = fetch_lfw_people(min_faces_per_person=2, color=True, resize=1.0)

print("Total photos:", len(lfw.images))
print("Total labels:", len(lfw.target_names))
