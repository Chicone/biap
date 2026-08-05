from PIL import Image

from vision.foundation_models.dinov2 import DinoV2


image = Image.open(
    "data/external/BBBC021/BBBC021_v1_images_Week10_40111/Week10_200907_B02_s1_w1A4CC66FD-CF75-4AEF-9C7B-05B8F2CC5A9B.tif"
)

model = DinoV2()

embedding = model.embed(image)

print(embedding.shape)