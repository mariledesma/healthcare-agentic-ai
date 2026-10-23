from db.database import init_database


def main():
    print(
        "Creating Healthcare Agentic AI database tables..."
    )

    init_database()

    print(
        "Database tables created successfully."
    )


if __name__ == "__main__":
    main()