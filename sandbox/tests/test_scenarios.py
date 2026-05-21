from sandbox.scenarios import SCENARIO_NAMES, create_scenario


def test_baseline_farming_scenario_can_be_created():
    scenario = create_scenario("baseline_farming")

    assert scenario.name == "baseline_farming"
    assert len(scenario.world.bot_controllers) == 1
    assert len(scenario.world.food_manager.items) > 0


def test_boundary_pressure_scenario_can_be_created():
    scenario = create_scenario("boundary_pressure")
    bot = next(s for s in scenario.world.snakes if s.id == scenario.bot_id)

    assert scenario.name == "boundary_pressure"
    assert bot.pos.length() > 0


def test_nearby_threat_scenario_can_be_created():
    scenario = create_scenario("nearby_threat")

    assert scenario.name == "nearby_threat"
    assert len(scenario.world.snakes) == 2


def test_mixed_food_and_threat_scenario_can_be_created():
    scenario = create_scenario("mixed_food_and_threat")

    assert scenario.name == "mixed_food_and_threat"
    assert len(scenario.world.snakes) == 2
    assert len(scenario.world.food_manager.items) > 1


def test_scenario_name_list_includes_required_scenarios():
    assert set(SCENARIO_NAMES) == {
        "baseline_farming",
        "boundary_pressure",
        "nearby_threat",
        "mixed_food_and_threat",
    }
