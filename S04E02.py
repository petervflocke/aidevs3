import json
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM
from tensorflow.keras.losses import BinaryCrossentropy
from tensorflow.keras.optimizers import Adam

# Function to read and parse feature data from files
def read_features(file):
    # Read file content and remove trailing whitespace
    with open(file, 'r') as f:
        content = f.read().rstrip()

    # Split content into lines
    lines = content.split("\n")

    # Convert each line into feature array by splitting on commas
    features = []
    for line in lines:
        features.append(line.split(','))

    return features

# Load training data from files
correct_features = read_features('S04E02/correct.txt')      # Load positive examples
incorrect_features = read_features('S04E02/incorrect.txt')   # Load negative examples
correct_sets_count = len(correct_features)
incorrect_sets_count = len(incorrect_features)

# Create binary labels (1 for correct, 0 for incorrect)
correct_targets = [1] * correct_sets_count
incorrect_targets = [0] * incorrect_sets_count

# Split data into training and validation sets
# Training: all except last 25 examples from each category
# Validation: last 25 examples from each category
training_features = np.array(correct_features[0:correct_sets_count-25] + incorrect_features[0:incorrect_sets_count-25], dtype=np.int64)
training_targets = np.array(correct_targets[0:correct_sets_count-25] + incorrect_targets[0:incorrect_sets_count-25], dtype=np.int64)
validation_features = np.array(correct_features[correct_sets_count-25:correct_sets_count] + incorrect_features[incorrect_sets_count-25:incorrect_sets_count], dtype=np.int64)
validation_targets = np.array(correct_targets[correct_sets_count-25:correct_sets_count] + incorrect_targets[incorrect_sets_count-25:incorrect_sets_count], dtype=np.int64)

# Load and prepare test data
test_features = read_features('S04E02/verify_no_lines.txt')
print(json.dumps(test_features, indent=4))
test_features = np.array(test_features, dtype=np.int64)

# Define model hyperparameters
activation_function = 'relu'
regularizer = 'l2'

# Create sequential neural network model
model = Sequential(
    [
        # First dense layer: 16 neurons with ReLU activation and L2 regularization
        Dense(units=16, activation=activation_function, kernel_regularizer=regularizer),
        # Second dense layer: 4 neurons with ReLU activation and L2 regularization
        Dense(units=4, activation=activation_function, kernel_regularizer=regularizer),
        # Output layer: 1 neuron with sigmoid activation for binary classification
        Dense(units=1, activation='sigmoid'),
    ]
)

# Compile model with binary cross-entropy loss and Adam optimizer
model.compile(
    optimizer=Adam(learning_rate=0.01),
    loss=BinaryCrossentropy()
)

# Train the model
model.fit(
    training_features,
    training_targets,
    epochs=500,          # Number of training iterations
    verbose=1,           # Show training progress
    shuffle=True,        # Shuffle data between epochs
    validation_data=(validation_features, validation_targets)  # Monitor validation performance
)

# Make predictions on test data
test_targets = model.predict(test_features)
print(json.dumps(test_targets.tolist(), indent=4))