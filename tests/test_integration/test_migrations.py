"""Tests for data migrations of the experiments app."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

BEFORE_TRIAL_TYPE = ("experiments", "0019_alter_experiment_demographic_data_page_tpl")
TRIAL_TYPE = ("experiments", "0020_trialitem_attention_getter_dwell")


def _migrate(target):
    """Migrate the experiments app to ``target`` and return its historical apps."""
    executor = MigrationExecutor(connection)
    executor.migrate([target])
    executor.loader.build_graph()
    return executor.loader.project_state([target]).apps


def _create_trial(apps, **fields):
    """Create a trial (with its parent hierarchy) using historical models."""
    user = apps.get_model("auth", "User").objects.create(username="migrator")
    experiment = apps.get_model("experiments", "Experiment").objects.create(
        exp_name="exp", user=user
    )
    listitem = apps.get_model("experiments", "ListItem").objects.create(
        list_name="list", experiment=experiment
    )
    outer = apps.get_model("experiments", "OuterBlockItem").objects.create(
        outer_block_name="outer", listitem=listitem
    )
    block = apps.get_model("experiments", "BlockItem").objects.create(
        label="block", outerblockitem=outer
    )
    return apps.get_model("experiments", "TrialItem").objects.create(
        label="trial", code="t1", max_duration=1000, blockitem=block, **fields
    )


@pytest.fixture
def migrator(transactional_db):
    """Yield ``_migrate`` and restore the latest schema afterwards."""
    yield _migrate
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.parametrize(
    ("is_calibration", "trial_type"), [(True, "CAL"), (False, "REG")]
)
def test_calibration_flag_becomes_trial_type(migrator, is_calibration, trial_type):
    """Existing calibration trials keep being calibration trials after 0020."""
    trial = _create_trial(migrator(BEFORE_TRIAL_TYPE), is_calibration=is_calibration)

    apps = migrator(TRIAL_TYPE)

    migrated = apps.get_model("experiments", "TrialItem").objects.get(pk=trial.pk)
    assert migrated.trial_type == trial_type


@pytest.mark.parametrize(
    ("trial_type", "is_calibration"), [("CAL", True), ("REG", False), ("AG", False)]
)
def test_trial_type_becomes_calibration_flag_on_reverse(
    migrator, trial_type, is_calibration
):
    """Reversing 0020 restores the calibration flag from the trial type."""
    trial = _create_trial(migrator(TRIAL_TYPE), trial_type=trial_type)

    apps = migrator(BEFORE_TRIAL_TYPE)

    migrated = apps.get_model("experiments", "TrialItem").objects.get(pk=trial.pk)
    assert migrated.is_calibration is is_calibration
