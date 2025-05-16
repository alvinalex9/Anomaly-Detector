from flask import Flask, render_template_string, request, send_file
import pandas as pd
import numpy as np
import plotly.express as px
import io
import os
import socket

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Anomaly Detection Tool</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css">
    <style>
        body { background-color: #f4f4f9; font-family: 'Segoe UI'; }
        .container { max-width: 960px; margin-top: 40px; }
    </style>
</head>
<body>
<div class="container text-center">
    <h3 class="mt-3">Anomaly Detection & Insights Dashboard</h3>
    <form action="/upload" method="post" enctype="multipart/form-data" class="mb-4">
        <input type="file" name="file" class="form-control mb-2" required>
        <button type="submit" class="btn btn-primary">Upload & Analyze</button>
    </form>
    {{ analysis|safe }}
</div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, analysis='')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return "<h4 style='color:red;'>No file uploaded.</h4>"

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        if df.empty:
            return "<h4 style='color:red;'>Uploaded file has no data.</h4>"

        # Missing Values
        missing_values = df.isnull().sum().reset_index()
        missing_values.columns = ['Column', 'Missing Values']

        # Error Patterns
        error_patterns = []
        for col in df.columns:
            for err in ['#REF!', '#N/A', '#DIV/0!', '#VALUE!']:
                count = df[col].astype(str).str.contains(err).sum()
                if count > 0:
                    error_patterns.append([err, col, count])

        error_df = pd.DataFrame(error_patterns, columns=['Error Type', 'Column', 'Count'])

        # Detailed Insights
        category_insights = "<h5>Category Insights:</h5>"
        for col in df.select_dtypes(include=['object', 'category']).columns:
            count_data = df[col].value_counts().nlargest(10).reset_index()
            count_data.columns = ['Value', 'Count']
            category_insights += f"<h6>{col} (Total: {df[col].count()})</h6>{count_data.to_html(classes='table table-bordered table-sm')}"

        summary_html = f'''<h5>Summary</h5>
        <h5>Missing Values:</h5>{missing_values.to_html(classes='table table-bordered')}
        <h5>Error Patterns:</h5>{error_df.to_html(classes='table table-bordered')}
        {category_insights}'''

        df.to_csv(os.path.join(UPLOAD_FOLDER, 'uploaded_data.csv'), index=False)

        return render_template_string(HTML_TEMPLATE, analysis=summary_html)

    except Exception as e:
        return f"<h4 style='color:red;'>Error processing file: {str(e)}</h4>"

@app.route('/visualize', methods=['POST'])
def visualize():
    try:
        df = pd.read_csv(os.path.join(UPLOAD_FOLDER, 'uploaded_data.csv'))
        columns = request.form.getlist('column')
        chart_type = request.form.get('chart_type')

        charts_html = ""
        for col in columns:
            if col in df.columns:
                if chart_type == 'pie':
                    fig = px.pie(df, names=col)
                elif chart_type == 'bar':
                    chart_data = df[col].value_counts().reset_index()
                    chart_data.columns = ['Category', 'Count']
                    fig = px.bar(chart_data, x='Category', y='Count', title=f"{col} Distribution")
                elif chart_type == 'histogram':
                    fig = px.histogram(df, x=col, title=f"{col} Histogram")
                else:
                    fig = px.line(df, x=df.index, y=col, title=f"{col} Line Chart")
                charts_html += fig.to_html(full_html=False)

        return f"<h5>Selected Charts:</h5>{charts_html}<br><a href='/'>Go Back</a>"

    except Exception as e:
        return f"<h4 style='color:red;'>Error generating chart: {str(e)}</h4><br><a href='/'>Go Back</a>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
