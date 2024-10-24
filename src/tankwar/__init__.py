import gymnasium

gymnasium.register(
    id="Tankwar-Base-v0",
    entry_point="tankwar.environment:TankwarEnv",
    nondeterministic=True,
)
