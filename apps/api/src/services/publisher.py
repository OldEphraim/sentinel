async def publish(routing_key: str, message: dict) -> None:
    print(f"[publisher stub] {routing_key}: {message}")
