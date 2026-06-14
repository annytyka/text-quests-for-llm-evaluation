import os
from collections import Counter

import matplotlib.pyplot as plt
import json


LABELS = {
    "gender": {
        "male": "Мужской",
        "female": "Женский",
    },

    "age": {
        "child": "до 12",
        "teen": "13–17",
        "young": "18–24",
        "adult": "25–35",
        "mid": "36–50",
        "senior": "50+",
    },

    "education": {
        "4": "4 класса",
        "9": "9 классов",
        "11": "11 классов",
        "college": "Колледж",
        "bachelor": "Бакалавриат",
        "master": "Магистратура / специалитет",
        "phd": "Аспирантура",
    },

    "study": {
        "yes": "Да",
        "no": "Нет",
    },

    "work": {
        "yes": "Да",
        "no": "Нет",
    },

    "played": {
        "yes": "Да",
        "no": "Нет",
    },
}


TITLES = {
    "gender": "Пол",
    "age": "Возраст",
    "education": "Образование",
    "study": "Учится",
    "work": "Работает",
    "played": "Играл в текстовые квесты ранее",
}


QUESTIONS = [
    "gender",
    "age",
    "education",
    "study",
    "work",
    "played",
]


def load_users(folder):
    users = []

    for filename in os.listdir(folder):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(folder, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                user = json.load(f)

            users.append(user)

        except Exception as e:
            print(f"Ошибка чтения {filename}: {e}")

    return users


def plot_survey_distributions(users,
                              output_dir="metrics/plots"):

    os.makedirs(output_dir, exist_ok=True)

    plt.rcParams["font.family"] = "DejaVu Sans"

    for question in QUESTIONS:

        values = [
            user.get("survey", {}).get(question)
            for user in users
            if user.get("survey", {}).get(question) is not None
        ]

        if not values:
            continue

        counter = Counter(values)

        ordered_keys = [
            key
            for key in LABELS[question]
            if key in counter
        ]

        labels = [
            LABELS[question][key]
            for key in ordered_keys
        ]

        counts = [
            counter[key]
            for key in ordered_keys
        ]

        total = sum(counts)

        shares = [
            count / total
            for count in counts
        ]

        plt.figure(figsize=(8, 5))

        bars = plt.bar(labels, shares)

        plt.title(
            f"{TITLES[question]}\n(n = {total})"
        )

        plt.ylabel("Доля пользователей")

        ymax = max(shares)

        plt.ylim(0, ymax * 1.15)

        plt.xticks(rotation=20)

        for bar, sh in zip(
            bars,
            shares
        ):
            plt.text(
                bar.get_x()
                + bar.get_width() / 2,
                bar.get_height(),
                f"{sh:.2f}",
                ha="center",
                va="bottom"
            )

        plt.tight_layout()

        out_path = os.path.join(
            output_dir,
            f"{question}.png"
        )

        plt.savefig(
            out_path,
            dpi=300,
            bbox_inches="tight"
        )

        plt.show()
        plt.close()


users = load_users("data_users_full")

plot_survey_distributions(users)