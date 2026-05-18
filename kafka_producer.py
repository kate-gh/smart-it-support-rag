from kafka import KafkaProducer
import json

producer = None

def get_producer():
    global producer

    if producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers="localhost:9092",
                value_serializer=lambda v:
                json.dumps(v).encode("utf-8")
            )

            print("[KAFKA] connected")

        except Exception as e:
            print(f"[KAFKA] unavailable: {e}")
            producer = False

    return producer


def publish_kb_update(question, answer, category, priority):

    data = {
        "question": question,
        "answer": answer,
        "category": category,
        "priority": priority
    }

    p = get_producer()

    if not p:
        print("[KAFKA] skipped")
        return

    try:

        p.send("kb_updates", data)
        p.flush()

        print("[KAFKA] envoyé :", question)

    except Exception as e:

        print("[KAFKA ERROR]", e)