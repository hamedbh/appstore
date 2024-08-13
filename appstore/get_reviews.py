import os
import datetime
import click
from authlib.jose import jwt
import requests
import json
from tqdm import tqdm
from dotenv import load_dotenv, find_dotenv


def sign_authlib(private_key_path, key_id, valid_for):
    current_time = int(datetime.datetime.now().timestamp())
    header = {"alg": "ES256", "kid": key_id, "typ": "JWT"}

    payload = {
        "iss": "69a6de77-4258-47e3-e053-5b8c7c11a4d1",
        "iat": current_time,
        "exp": current_time + valid_for,
        "aud": "appstoreconnect-v1",
    }
    with open(private_key_path, "rb") as fh:
        signing_key = fh.read()
    token = jwt.encode(header, payload, key=signing_key)
    decoded = token.decode()
    return decoded


def parse_review_dict(d):
    out = {
        "id": d["id"],
        "rating": d["attributes"]["rating"],
        "review": d["attributes"]["body"],
        "date": d["attributes"]["createdDate"][:10],
    }
    return out


@click.command()
@click.option("-k", "--key-id", required=True, help="Key ID")
@click.option("-a", "--app-id", required=True, help="App ID")
@click.option(
    "-o",
    "--output-path",
    required=True,
    default="reviews.json",
    help="Output file",
)
def get_reviews(key_id, app_id, output_path):
    private_key_path = os.environ["P8_KEY_PATH"]
    limit = 200
    next_url = "".join(
        [
            "https://api.appstoreconnect.apple.com/v1/apps/",
            app_id,
            "/customerReviews?limit=",
            str(limit),
            "&sort=createdDate",
        ]
    )
    signed_key = sign_authlib(private_key_path, key_id, 1200)
    n_reviews = requests.get(
        next_url,
        headers={"Authorization": f"Bearer {signed_key}"},
    ).json()["meta"]["paging"]["total"]
    n_pages = (n_reviews // limit) + 1

    out = []
    has_more = True
    for i in tqdm(range(0, n_pages)):
        r = requests.get(
            next_url, headers={"Authorization": f"Bearer {signed_key}"}
        ).json()
        parsed_reviews = [parse_review_dict(d) for d in r["data"]]
        for review in parsed_reviews:
            out.append(review)
        next_url = r["links"].get("next", "")
        has_more = "next" in r["links"]
    if has_more:
        raise ValueError(
            "More reviews to collect, n_pages calculated incorrectly."
        )
    with open(output_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Written {n_reviews} reviews to {output_path}")
    return n_reviews


if __name__ == "__main__":
    load_dotenv(find_dotenv())
    get_reviews()
