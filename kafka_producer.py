from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def publish_kb_update(question, answer, category, priority):
    data = {
        "question": question,
        "answer": answer,
        "category": category,
        "priority": priority
    }

    producer.send("kb_updates", data)
    producer.flush()

    print(" [KAFKA] envoyé :", question)