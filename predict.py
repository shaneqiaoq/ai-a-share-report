import pandas as pd
import matplotlib.pyplot as plt

# Read data
df = pd.read_csv('biomed_data.csv', index_col=0)

# Transpose data for plotting
df_t = df.T

# Plotting
plt.figure(figsize=(10, 6))

for column in df_t.columns:
    plt.plot(df_t.index, df_t[column], marker='o', label=column)

plt.title('Biomed Patent Trends (2010-2024)')
plt.xlabel('Year')
plt.ylabel('Patent Count')
plt.legend(title='City')
plt.grid(True)

# Save image
plt.savefig('trend_result.png')
