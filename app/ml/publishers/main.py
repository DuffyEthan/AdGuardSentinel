from app.ml.publishers.pub_cat import pub_cat
from app.ml.publishers.pub_dog import pub_dog
from app.ml.publishers.pub_fox import pub_fox
from app.ml.publishers.pub_owl import pub_owl
from app.ml.publishers.pub_spy import pub_spy

publisherCatalog={
    "cat":pub_cat,
    "dog":pub_dog,
    "fox":pub_fox,
    "owl":pub_owl,
    "spy":pub_spy
}

if __name__=="__main__":
    print("Hello, World!")
