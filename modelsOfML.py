# %%
!pip install keras-tuner
!pip install lime

# %%
# importing the Libraries
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import GridSearchCV
from keras_tuner import Hyperband
import tensorflow as tf
import lime
import lime.lime_tabular

# %%
# load the predictive maintenance dataset
Pred_main_data = pd.read_csv('archive\\ai4i2020.csv')
Pred_main_data

# %% [markdown]
# # Initial Findings

# %%
# Remove the 'UDI' and 'Product ID' columns
Pred_main_data = Pred_main_data.drop(columns=['UDI', 'Product ID'])

# Encode the 'type' column categorical variables(low, mediam, high quality)
Pred_main_data['Type'] = Pred_main_data['Type'].map({'L': 0, 'M': 1, 'H': 2})

# statistics of the dataset
Pred_main_data.describe()

# %%
# Checking the missing values
print(Pred_main_data.isnull().sum())

# %%
# Check the data types of each column
print(Pred_main_data.dtypes)

# %%
# print the count of target variables
Pred_main_data['Machine failure'].value_counts()

# %% [markdown]
# # EDA

# %%
# List of numerical features
numerical_features = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']

# Plot histograms for numerical features
for feature in numerical_features:
    plt.figure(figsize=(10, 6))
    sns.histplot(Pred_main_data[feature], kde=True)
    plt.title(f'Distribution of {feature}', fontsize=22)
    plt.xlabel(feature,fontsize=22)
    plt.ylabel('Frequency',fontsize=22)
    plt.show()

# %%
# Plot box plots for numerical features
for feature in numerical_features:
    plt.figure(figsize=(10, 6))
    sns.boxplot(x=Pred_main_data[feature])
    plt.title(f'Boxplot of {feature}')
    plt.xlabel(feature)
    plt.show()

# %%
# Define a function to remove outliers based on IQR
def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
    return df

# Remove outliers from 'Rotational speed [rpm]' and 'Torque [Nm]'
df = remove_outliers(Pred_main_data, 'Rotational speed [rpm]')
df = remove_outliers(Pred_main_data, 'Torque [Nm]')

# Verify the result
print("Dataset shape after removing outliers:", df.shape)

# %%
Pred_main_data['Machine failure'].value_counts()

# %%
# Plot count plot for the 'Type' feature
plt.figure(figsize=(10, 6))
sns.countplot(x='Type', data=Pred_main_data)
plt.title('Distribution of Type')
plt.xlabel('Type')
plt.ylabel('Frequency')
plt.xticks(ticks=[0, 1, 2], labels=['L', 'M', 'H'])
plt.show()

# Plot count plot for the 'Machine failure' feature
plt.figure(figsize=(10, 6))
sns.countplot(x='Machine failure', data=Pred_main_data)
plt.title('Distribution of Machine Failure')
plt.xlabel('Machine Failure')
plt.ylabel('Frequency')
plt.show()

# %%
# Separate features and target
X = Pred_main_data.drop(columns=['Machine failure'])
y = Pred_main_data['Machine failure']

# Apply SMOTE
smote = SMOTE(random_state=42)
X_res, y_res = smote.fit_resample(X, y)

# Combine the resampled features and target into a new DataFrame
df_resampled = pd.concat([pd.DataFrame(X_res, columns=X.columns), pd.DataFrame(y_res, columns=['Machine failure'])], axis=1)

# %%
df_resampled['Machine failure'].value_counts()

# %%
df_resampled.shape

# %%
# Select numerical columns to normalize (excluding 'Machine failure' if it's your target variable)
numerical_cols = df_resampled.drop(columns=['Machine failure']).columns

# Initialize the StandardScaler
scaler = MinMaxScaler()

# Fit and transform the numerical columns
df_resampled[numerical_cols] = scaler.fit_transform(df_resampled[numerical_cols])

# Display the first few rows to check the normalized data
df_resampled.head()

# %%
# Define colors for 'Failure' (red) and 'No Failure' (blue)
failure_colors = {0: 'blue', 1: 'red'}

plt.figure(figsize=(10, 6))
# Plot scatter plot with specific colors
sns.scatterplot(x='Rotational speed [rpm]', y='Torque [Nm]', hue='Machine failure', data=df_resampled,
                palette=failure_colors)

plt.title('Rotational Speed vs Torque')
plt.xlabel('Rotational Speed [rpm]')
plt.ylabel('Torque [Nm]')

# Create custom legend
legend_labels = ['No Failure', 'Failure']
legend_handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10) for color in failure_colors.values()]
plt.legend(legend_handles, legend_labels, title='Machine Failure')

plt.show()

# %%
# Calculate the correlation matrix
correlation_matrix = df_resampled.corr()

# Plot the heatmap
plt.figure(figsize=(14, 10))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Heatmap')
plt.show()

# %%
# Separate features and target variable
X = df_resampled.drop(columns=['Machine failure'])
y = df_resampled['Machine failure']

# Apply PCA to reduce dimensionality
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_pca, y, test_size=0.2, random_state=42)

# Printing the shapes of train and test sets
print("X_train shape:", X_train.shape)
print("X_test shape:", X_test.shape)
print("y_train shape:", y_train.shape)
print("y_test shape:", y_test.shape)

# %% [markdown]
# # MODEL IMPLEMENTATION

# %% [markdown]
# ## Random Forest

# %%
# Initialize the Random Forest model
Prmain_rf = RandomForestClassifier(random_state=42)

# Fit the model on the training data
Prmain_rf.fit(X_train, y_train)

# Get predictions from the Random Forest model
y_pred_rf_train = Prmain_rf.predict(X_train)
y_pred_rf_test = Prmain_rf.predict(X_test)

# %%
# Prepare the input for the neural network by combining original features and RF predictions
X_train_nn = np.column_stack((X_train, y_pred_rf_train))
X_test_nn = np.column_stack((X_test, y_pred_rf_test))

# Define the neural network architecture
model_rf = Sequential()
model_rf.add(Dense(64, input_dim=X_train_nn.shape[1], activation='relu'))
model_rf.add(Dense(32, activation='relu'))
model_rf.add(Dense(1, activation='sigmoid'))  # Use 'sigmoid' for binary classification

# Compile the model
model_rf.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

early_stopping = EarlyStopping(monitor='val_loss',
    patience=3,
    restore_best_weights=True)
# Train the neural network
rf_hystory = model_rf.fit(X_train_nn, y_train, epochs=50, batch_size=32, validation_split=0.2, callbacks=[early_stopping])

# %%
def plot_training_history(history, title='Model Training History'):
    """
    Plots the training and validation loss and accuracy from the model's history.

    Args:
    - history: History object returned by the model's fit method.
    - title: Title of the plot (string).

    Returns:
    - None: Displays the plot.
    """
    plt.figure(figsize=(12, 6))

    # Plotting loss
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Training Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title(f'{title} - Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()

    # Plotting accuracy
    plt.subplot(1, 2, 2)
    plt.plot(history.history['accuracy'], label='Training Accuracy')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
    plt.title(f'{title} - Accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()

    plt.show()

# %%
plot_training_history(rf_hystory, title='Hybrid NN and RF Training History')

# %%
# Predict on the test set using the neural network
y_pred_rf_test = model_rf.predict(X_test_nn)

y_pred_rf_test = (y_pred_rf_test > 0.5).astype(int)

# %%
def evaluate_predictive_maintenance_model(y_true, y_pred):
    """
    Prints the classification report and visualizes the confusion matrix.

    Parameters:
    - y_true: Ground truth target values.
    - y_pred: Estimated targets as returned by a classifier.
    - class_names: List of class names for labeling the confusion matrix.

    Returns:
    - None
    """
    class_names = ['No Failure', 'Failure']

    # Print classification report
    print('Classification Report:')
    print(classification_report(y_true, y_pred, target_names=class_names))

    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    # Visualize confusion matrix
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=class_names, yticklabels=class_names)
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.title('Confusion Matrix')
    plt.show()

# %%
evaluate_predictive_maintenance_model(y_test, y_pred_rf_test)

# %% [markdown]
# ## Gradient Boosting

# %%
# Initialize the Gradient Boosting model
gbc = GradientBoostingClassifier(random_state=42)

# Fit the model on the training data
gbc.fit(X_train, y_train)

# Get predictions from the Gradient Boosting model
y_pred_gbc_train = gbc.predict(X_train)
y_pred_gbc_test = gbc.predict(X_test)

X_train_nn_gbc = np.column_stack((X_train, y_pred_gbc_train))
X_test_nn_gbc = np.column_stack((X_test, y_pred_gbc_test))

# Define the neural network architecture
model_gbc = Sequential()
model_gbc.add(Dense(64, input_dim=X_train_nn_gbc.shape[1], activation='relu'))
model_gbc.add(Dense(32, activation='relu'))
model_gbc.add(Dense(1, activation='sigmoid'))

# Compile the model
model_gbc.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Train the neural network
gbc_history = model_gbc.fit(X_train_nn_gbc, y_train, epochs=50, batch_size=32, validation_split=0.2, callbacks=[early_stopping])

# Predict on the test set using the neural network
y_pred_nn_gbc_test = model_gbc.predict(X_test_nn_gbc)
y_pred_nn_gbc_test = (y_pred_nn_gbc_test > 0.5).astype(int)


# %%
plot_training_history(gbc_history, title='Hybrid NN and GBC Training History')

# %%
evaluate_predictive_maintenance_model(y_test, y_pred_nn_gbc_test)

# %% [markdown]
# ## SVM

# %%
# Initialize the SVM model
svm = SVC(probability=True, random_state=42)

# Fit the model on the training data
svm.fit(X_train, y_train)

# Get predictions from the SVM model
y_pred_svm_train = svm.predict(X_train)
y_pred_svm_test = svm.predict(X_test)

# Prepare the input for the neural network by combining original features and SVM predictions
X_train_nn_svm = np.column_stack((X_train, y_pred_svm_train))
X_test_nn_svm = np.column_stack((X_test, y_pred_svm_test))

# Define the neural network architecture
model_svm = Sequential()
model_svm.add(Dense(64, input_dim=X_train_nn_svm.shape[1], activation='relu'))
model_svm.add(Dense(32, activation='relu'))
model_svm.add(Dense(1, activation='sigmoid'))  # Use 'sigmoid' for binary classification

# Compile the model
model_svm.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Train the neural network
svm_history = model_svm.fit(X_train_nn_svm, y_train, epochs=50, batch_size=32, validation_split=0.2, callbacks=[early_stopping])

# Predict on the test set using the neural network
y_pred_nn_svm_test = model_svm.predict(X_test_nn_svm)
y_pred_nn_svm_test = (y_pred_nn_svm_test > 0.5).astype(int)


# %%
plot_training_history(svm_history, title='Hybrid NN and SVM Training History')

# %%
evaluate_predictive_maintenance_model(y_test, y_pred_nn_svm_test)

# %% [markdown]
# ## KNN

# %%
# Initialize the KNN model
knn = KNeighborsClassifier(n_neighbors=5)

# Fit the model on the training data
knn.fit(X_train, y_train)

# Get predictions from the KNN model
y_pred_knn_train = knn.predict(X_train)
y_pred_knn_test = knn.predict(X_test)

# Prepare the input for the neural network by combining original features and KNN predictions
X_train_nn_knn = np.column_stack((X_train, y_pred_knn_train))
X_test_nn_knn = np.column_stack((X_test, y_pred_knn_test))

# Define the neural network architecture
model_knn = Sequential()
model_knn.add(Dense(64, input_dim=X_train_nn_knn.shape[1], activation='relu'))
model_knn.add(Dense(32, activation='relu'))
model_knn.add(Dense(1, activation='sigmoid'))  # Use 'sigmoid' for binary classification

# Compile the model
model_knn.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Train the neural network
knn_history = model_knn.fit(X_train_nn_knn, y_train, epochs=50, batch_size=32, validation_split=0.2, callbacks=[early_stopping])

# Predict on the test set using the neural network
y_pred_nn_knn_test = model_knn.predict(X_test_nn_knn)
y_pred_nn_knn_test = (y_pred_nn_knn_test > 0.5).astype(int)

# %%
plot_training_history(knn_history, title='Hybrid NN and KNN Training History')

# %%
evaluate_predictive_maintenance_model(y_test, y_pred_nn_knn_test)

# %% [markdown]
# ## ANN

# %%
# Initialize the ANN model
Prmain_ann = Sequential()
Prmain_ann.add(Dense(64, activation='relu', input_shape=(X_train.shape[1],)))  # Input layer
Prmain_ann.add(Dense(32, activation='relu'))  # Hidden layer
Prmain_ann.add(Dense(1, activation='sigmoid'))  # Output layer for binary classification

# Compile the model
Prmain_ann.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

early_stopping = EarlyStopping(monitor='val_loss',
    patience=10,
    restore_best_weights=True)

# Fit the model on the training data
history = Prmain_ann.fit(X_train, y_train, epochs=100, batch_size=32, validation_split=0.2, callbacks=[early_stopping])

# %%
# Plot training & validation loss values
plt.figure(figsize=(12, 6))

# Loss plot
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.tight_layout()
plt.show()

# Plot training & validation accuracy values
plt.figure(figsize=(12, 6))

# Accuracy plot
plt.subplot(1, 2, 2)
plt.plot(history.history['accuracy'], label='Training Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('Model Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()

plt.tight_layout()
plt.show()

# %%
# Predict on the test set
y_pred_prob_Prmain_ann = Prmain_ann.predict(X_test)
y_pred_Prmain_ann = y_pred_prob_Prmain_ann.argmax(axis=1)

# Print the classification report
print("Classification Report:")
print(classification_report(y_test, y_pred_Prmain_ann, target_names=['No Failure', 'Failure']))

# Compute the confusion matrix
cm = confusion_matrix(y_test, y_pred_Prmain_ann)

# Plot the confusion matrix
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['No Failure', 'Failure'], yticklabels=['No Failure', 'Failure'])
plt.xlabel('Predicted Labels')
plt.ylabel('True Labels')
plt.title('Confusion Matrix for ANN')
plt.show()

# %% [markdown]
# # Model implementation with hyperparametertuining

# %% [markdown]
# ## Random Forest

# %%
# Define the parameter grid
rf_param_grid = {
    'min_samples_split': [2, 5],
    'min_samples_leaf': [1, 2],
    'bootstrap': [True, False],
    'n_estimators': [100, 200],
    'max_depth': [None, 10, 20],
}


Prmain_rf = RandomForestClassifier(random_state=42)

grid_search = GridSearchCV(estimator=Prmain_rf, param_grid=rf_param_grid,
                           cv=3, n_jobs=-1, verbose=2, scoring='accuracy')

# Fit the grid search to the data
grid_search.fit(X_train, y_train)

# Best hyperparameters from the grid search
best_params = grid_search.best_params_
print(f"Best hyperparameters: {best_params}")

# Best Random Forest model
Prmain_best_rf = grid_search.best_estimator_

# Make predictions
y_pred_Prmain_rf_hy = Prmain_best_rf.predict(X_test)

# %%
evaluate_predictive_maintenance_model(y_test, y_pred_Prmain_rf_hy)

# %% [markdown]
# ## Gradient Boosting

# %%
gb_param_grid = {
    'n_estimators': [100, 200],          # Number of boosting stages to be run
    'min_samples_split': [2, 5],          # Minimum number of samples required to split a node
    'min_samples_leaf': [1, 2],            # Minimum number of samples required at each leaf node
    'subsample': [0.8, 0.9],              # Fraction of samples used for fitting the individual base learners
     'learning_rate': [0.01, 0.1],        # Learning rate shrinks the contribution of each tree
    'max_depth': [3, 4]                  # Maximum depth of the individual estimators
}

# Initialize a GradientBoostingClassifier
Prmain_gb = GradientBoostingClassifier(random_state=42)

# Initialize GridSearchCV
grid_search_gb = GridSearchCV(estimator=Prmain_gb, param_grid=gb_param_grid,
                              cv=3, n_jobs=-1, verbose=2, scoring='accuracy')

# Fit the grid search to the data
grid_search_gb.fit(X_train, y_train)

# Best hyperparameters from the grid search
best_params_gb = grid_search_gb.best_params_
print(f"Best hyperparameters: {best_params_gb}")

# Best Gradient Boosting model
Prmain_best_gb = grid_search_gb.best_estimator_

# Make predictions
y_pred_Prmain_gb_hy = Prmain_best_gb.predict(X_test)

# %%
evaluate_predictive_maintenance_model(y_test, y_pred_Prmain_gb_hy)

# %% [markdown]
# ## SVM

# %%
# Define the parameter grid
svm_param_grid = {
    'C': [0.1, 1],
    'gamma': ['scale', 'auto'],
    'kernel': ['rbf', 'linear', 'sigmoid']
}

# Initialize an SVC (Support Vector Classifier)
Prmain_svc = SVC()

# Initialize GridSearchCV
grid_search_svc = GridSearchCV(estimator=Prmain_svc, param_grid=svm_param_grid,
                               cv=3, n_jobs=-1, verbose=2, scoring='accuracy')

# Fit the grid search to the data
grid_search_svc.fit(X_train, y_train)

# Best hyperparameters from the grid search
best_params_svc = grid_search_svc.best_params_
print(f"Best hyperparameters: {best_params_svc}")

# Best SVM model
Prmain_best_svc = grid_search_svc.best_estimator_

# Make predictions
y_pred_Prmain_svc_hy = Prmain_best_svc.predict(X_test)

# %%
evaluate_predictive_maintenance_model(y_test, y_pred_Prmain_svc_hy)

# %% [markdown]
# ## KNN

# %%
# Define the parameter grid
knn_param_grid = {
    'n_neighbors': [3, 5, 7],  # Number of neighbors to use
    'weights': ['uniform', 'distance'],  # Weight function used in prediction
    'metric': ['euclidean', 'manhattan']  # Distance metric
}

# Initialize a KNeighborsClassifier
Prmain_knn = KNeighborsClassifier()

# Initialize GridSearchCV
grid_search_knn = GridSearchCV(estimator=Prmain_knn, param_grid=knn_param_grid,
                               cv=3, n_jobs=-1, verbose=2, scoring='accuracy')

# Fit the grid search to the data
grid_search_knn.fit(X_train, y_train)

# Best hyperparameters from the grid search
best_params_knn = grid_search_knn.best_params_
print(f"Best hyperparameters: {best_params_knn}")

# Best KNN model
best_knn = grid_search_knn.best_estimator_

# Make predictions
y_pred_knn_Prmain_hy = best_knn.predict(X_test)

# %%
evaluate_predictive_maintenance_model(y_test, y_pred_knn_Prmain_hy)

# %% [markdown]
# ## ANN

# %%
def build_model(hp):
    model = Sequential()
    model.add(Dense(units=hp.Int('units1', min_value=32, max_value=128, step=32), activation='relu', input_shape=(X_train.shape[1],)))
    model.add(Dense(units=hp.Int('units2', min_value=16, max_value=64, step=16), activation='relu'))
    model.add(Dense(1, activation='sigmoid'))

    model.compile(
        optimizer=tf.keras.optimizers.Adam(hp.Float('learning_rate', min_value=1e-4, max_value=1e-2, sampling='LOG')),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return model

# %%
tuner = Hyperband(
    build_model,
    objective='val_accuracy',
    max_epochs=20,
    hyperband_iterations=1,
    directory='project_dir',
    project_name='ann_hyperparameter_tuning'
)

stop_early = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

tuner.search(X_train, y_train, epochs=50, validation_split=0.2, callbacks=[stop_early])

# %%
# Get the best hyperparameters
best_hyperparameters = tuner.get_best_hyperparameters()[0]

# Print the best hyperparameters
print("Best Hyperparameters:")
print(f"Number of units in first Dense layer: {best_hyperparameters.get('units1')}")
print(f"Number of units in second Dense layer: {best_hyperparameters.get('units2')}")
print(f"Learning rate: {best_hyperparameters.get('learning_rate')}")

# %%
best_model = tuner.get_best_models(num_models=1)[0]
history = best_model.fit(X_train, y_train, epochs=50, validation_split=0.2, callbacks=[stop_early])

# %%
# Plot training history
plt.figure(figsize=(12, 6))
plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='Accuracy')
plt.plot(history.history['val_accuracy'], label = 'Validation Accuracy')
plt.title('Model Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.show()

# %%
# Predict on the test set
y_pred_prob_Prmain_ann = best_model.predict(X_test)
y_pred_Prmain_ann = y_pred_prob_Prmain_ann.argmax(axis=1)

# Print the classification report
print("Classification Report:")
print(classification_report(y_test, y_pred_Prmain_ann, target_names=['No Failure', 'Failure']))

# Compute the confusion matrix
cm = confusion_matrix(y_test, y_pred_Prmain_ann)

# Plot the confusion matrix
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['No Failure', 'Failure'], yticklabels=['No Failure', 'Failure'])
plt.xlabel('Predicted Labels')
plt.ylabel('True Labels')
plt.title('Confusion Matrix for ANN')
plt.show()

# %% [markdown]
# # Future Importance Analysis with LIME

# %%
# Separate features and target variable
X_data = df_resampled.drop(columns=['Machine failure'])
y_data = df_resampled['Machine failure']


# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_data, y_data, test_size=0.2, random_state=42)

# Printing the shapes of train and test sets
print("X_train shape:", X_train.shape)
print("X_test shape:", X_test.shape)
print("y_train shape:", y_train.shape)
print("y_test shape:", y_test.shape)

# %%
# Define the hyperparameters for the Random Forest model
params = {
    'bootstrap': True,
    'max_depth': 20,
    'min_samples_leaf': 1,
    'min_samples_split': 2,
    'n_estimators': 200
}

# Initialize the Random Forest model with the specified hyperparameters
Best_rf_model = RandomForestClassifier(
    bootstrap=params['bootstrap'],
    max_depth=params['max_depth'],
    min_samples_leaf=params['min_samples_leaf'],
    min_samples_split=params['min_samples_split'],
    n_estimators=params['n_estimators'],
    random_state=42  # Set a random state for reproducibility
)

# Fit the model to your training data
Best_rf_model.fit(X_train, y_train)

# %%
# Initialize the LIME explainer
explainer = lime.lime_tabular.LimeTabularExplainer(
    training_data=np.array(X_train),
    feature_names=X_train.columns,
    class_names=['Not Failed', 'Failed'],
    mode='classification'
)

instance = X_test.iloc[0]

# Generate LIME explanation for the chosen instance
lime_exp = explainer.explain_instance(
    data_row=instance,
    predict_fn=Best_rf_model.predict_proba
)

# Visualize the LIME explanation
lime_exp.show_in_notebook(show_table=True)

# Extract feature importances from the LIME explanation
importance_df = pd.DataFrame(lime_exp.as_list(), columns=['Feature', 'Importance'])

# Sort the DataFrame by importance in descending order
importance_df = importance_df.sort_values(by='Importance', ascending=False)

# Plot feature importance using LIME values
plt.figure(figsize=(12, 8))
sns.barplot(x='Importance', y='Feature', data=importance_df)
plt.title('Feature Importance from LIME (Random Forest Model)')
plt.xlabel('Importance')
plt.ylabel('Feature')
plt.show()


