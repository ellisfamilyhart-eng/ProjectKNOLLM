import json
import os
import tempfile
from jarvix.neural_learner import NeuralLearner, TinyBrain
from jarvix.memory_store import MemoryStore

def test_text_to_features():
    nl = NeuralLearner(None)  # memory not used for this method
    features = nl.text_to_features("Hi", max_len=10)
    assert len(features) == 10
    # 'H' -> (72-32)/96 = 40/96 ≈ 0.4167, 'i' -> (105-32)/96 = 73/96 ≈ 0.7604
    assert abs(features[0] - 0.4167) < 0.001
    assert abs(features[1] - 0.7604) < 0.001
    # rest zeros
    assert all(f == 0.0 for f in features[2:])

def test_neural_learner_training():
    # Create a temporary memory file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({}, f)
        temp_file = f.name

    try:
        memory = MemoryStore(data_file=temp_file)
        nl = NeuralLearner(memory, feature_size=8)
        # Train on a simple fact
        loss = nl.learn_topic_pattern("test_topic", "hello world", 0.8)
        assert isinstance(loss, float)
        # Predict
        pred, has_net = nl.predict_topic_pattern("test_topic", "hello world")
        assert has_net
        assert 0.0 <= pred <= 1.0
        # Global network
        gl_loss = nl.learn_global_pattern("hello world", 0.8)
        assert isinstance(gl_loss, float)
        gl_pred = nl.predict_global_pattern("hello world")
        assert 0.0 <= gl_pred <= 1.0
    finally:
        os.unlink(temp_file)

def test_neural_learner_batch():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({}, f)
        temp_file = f.name

    try:
        memory = MemoryStore(data_file=temp_file)
        nl = NeuralLearner(memory, feature_size=8)
        facts = [("hello", 0.9), ("world", 0.1)]
        avg_loss = nl.batch_learn_topic("test_topic", facts, epochs=2)
        assert isinstance(avg_loss, float)
    finally:
        os.unlink(temp_file)

if __name__ == "__main__":
    test_text_to_features()
    test_neural_learner_training()
    test_neural_learner_batch()
    print("All tests passed")