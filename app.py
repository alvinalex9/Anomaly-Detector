from flask import Flask, render_template_string, request, send_file
import pandas as pd
import numpy as np
import plotly.express as px
import io
import os
import socket

app = Flask(__name__)

UPLOAD_FOLDER = r'\uploads'
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
        .btn- { background-color: #ffc72c; color: black; font-weight: bold; }
        .-logo { width: 130px; }
        footer { margin-top: 20px; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
<div class="container text-center">
    <img src="/static/assets/logo.png" class="-logo" alt=" Logo">
    <h3 class="mt-3">Anomaly Detection & Insights Dashboard</h3>
    <form action="/upload" method="post" enctype="multipart/form-data" class="mb-4">
        <input type="file" name="file" class="form-control mb-2" required>
        <button type="submit" class="btn btn-">Upload & Analyze</button>
    </form>
    {{ analysis|safe }}
    <div id="charts"></div>
    <footer>© Anomaly Detection Tool - All rights reserved.</footer>
</div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, analysis='')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if not file: return "No file uploaded."

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    try:
        df = pd.read_excel(file_path) if file.filename.endswith('.xlsx') else pd.read_csv(file_path)
        df.to_csv(os.path.join(UPLOAD_FOLDER, 'uploaded_data.csv'), index=False)
    except Exception as e:
        return f"<h4 style='color:red;'>Error reading file: {e}</h4>"

    if df.empty:
        return "<h4 style='color:red;'>Uploaded file has no data.</h4>"

    # Missing Values
    missing_values = df.isnull().sum()
    missing_values = missing_values[missing_values > 0].reset_index()
    missing_values.columns = ['Column', 'Missing Values']

    # Error Patterns
    error_patterns = []
    for col in df.columns:
        for err in ['#REF!', '#N/A', '#DIV/0!', '#VALUE!']:
            count = df[col].astype(str).str.contains(err).sum()
            if count > 0:
                error_patterns.append([err, col, count])

    error_df = pd.DataFrame(error_patterns, columns=['Error Type', 'Column', 'Count'])

    if error_df.empty:
        error_html = "<h5>No Error Patterns Detected.</h5>"
    else:
        error_html = f"<h5>Error Patterns:</h5>{error_df.to_html(classes='table table-bordered')}"

    # Detailed Insights
    category_insights = "<h5>Category Insights:</h5>"
    for col in df.select_dtypes(include=['object']).columns:
        count_data = df[col].value_counts().nlargest(10).reset_index()
        count_data.columns = ['Value', 'Count']
        if len(count_data) > 0:
            category_insights += f"<h6>{col} (Total: {df[col].count()})</h6>{count_data.to_html(classes='table table-bordered table-sm')}"

    summary_html = f'''<h5>Summary</h5>
    <h5>Missing Values:</h5>{missing_values.to_html(classes='table table-bordered')}
    {error_html}
    {category_insights}
    <form method='post' action='/visualize'>
        <select name='column' multiple class="form-control mt-2">
            {''.join([f"<option value='{col}'>{col} (Total: {df[col].nunique()} unique)</option>" for col in df.columns])}
        </select>
        <select name='chart_type' class="form-control mt-2">
            <option value='bar'>Bar Chart</option>
            <option value='pie'>Pie Chart</option>
            <option value='line'>Line Chart</option>
            <option value='histogram'>Histogram</option>
        </select>
        <button type='submit' class='btn btn- mt-3'>Generate Charts</button>
    </form>'''

    return render_template_string(HTML_TEMPLATE, analysis=summary_html)

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
    port = socket.socket()
    port.bind(('', 0))
    p = port.getsockname()[1]
    port.close()
    print(f"Running on http://localhost:{p}")
    app.run(debug=False, port=p)
