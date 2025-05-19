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
        .logo { width: 150px; }
    </style>
    <script>
            function toggleYAxis() {
                const chartType = document.getElementById("chart_type").value;
                const yAxisDiv = document.getElementById("y_axis_div");
                if (chartType === "bar" || chartType === "pie") {
                    yAxisDiv.style.display = "none";
                } else {
                    yAxisDiv.style.display = "block";
                }
            }
        </script>
    
</head>
<body>
<div class="container text-center">
    <img src="https://img.freepik.com/premium-vector/company-logo-design_1043168-13606.jpg" class="logo" alt="Company Logo">
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
        missing_values = df.isnull().sum()
        missing_values = missing_values[missing_values > 0].reset_index()
        missing_values.columns = ['Column', 'Missing Values']

        if missing_values.empty:
            missing_html = "<h5>No Missing Values Detected.</h5>"
        else:
            missing_html = f"<h5>Missing Values:</h5>{missing_values.to_html(classes='table table-bordered')}"

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

        summary_html = f'''<h5>Summary</h5>{missing_html}{error_html}{category_insights}
        <form method='post' action='/visualize'>
        <label>Select X-Axis Column:</label>
        <select name='x_axis' class="form-control mt-2">
            {''.join([f"<option value='{col}'>{col}</option>" for col in df.columns])}
        </select>

        <div id="y_axis_div">
            <label>Select Y-Axis Column:</label>
            <select name='y_axis' class="form-control mt-2">
                {''.join([f"<option value='{col}'>{col}</option>" for col in df.select_dtypes(include=['number']).columns])}
            </select>
        </div>

        <label>Select Chart Type:</label>
        <select name='chart_type' id='chart_type' class="form-control mt-2" onchange="toggleYAxis()">
            <option value='bar'>Bar Chart</option>
            <option value='pie'>Pie Chart</option>
            <option value='scatter'>Scatter Plot</option>
            <option value='box'>Box Plot</option>
            <option value='area'>Area Plot</option>
            <option value='heatmap'>Heatmap</option>
        </select>
        
        <button type='submit' class='btn btn-primary mt-3'>Generate Charts</button>
        </form>'''


        df.to_csv(os.path.join(UPLOAD_FOLDER, 'uploaded_data.csv'), index=False)

        return render_template_string(HTML_TEMPLATE, analysis=summary_html)

    except Exception as e:
        return f"<h4 style='color:red;'>Error processing file: {str(e)}</h4>"

@app.route('/visualize', methods=['POST'])
def visualize():
    try:
        df = pd.read_csv(os.path.join(UPLOAD_FOLDER, 'uploaded_data.csv'))
        x_col = request.form.get('x_axis')
        y_col = request.form.get('y_axis')
        chart_type = request.form.get('chart_type')

        if x_col not in df.columns:
            return "<h4 style='color:red;'>Invalid X-axis column selected.</h4>"

        if chart_type not in ['bar', 'pie'] and (y_col not in df.columns):
            return "<h4 style='color:red;'>Invalid Y-axis column selected for this chart type.</h4>"

        if chart_type == 'bar':
            data = df[x_col].value_counts().reset_index()
            data.columns = ['Category', 'Count']
            fig = px.bar(data, x='Category', y='Count', title=f"{x_col} Distribution")

        elif chart_type == 'pie':
            data = df[x_col].value_counts().reset_index()
            data.columns = ['Category', 'Count']
            fig = px.pie(data, names='Category', values='Count', title=f"{x_col} Distribution")

        elif chart_type == 'scatter':
            fig = px.scatter(df, x=x_col, y=y_col, title=f"{x_col} vs {y_col} Scatter Plot")

        elif chart_type == 'box':
            fig = px.box(df, x=x_col, y=y_col, title=f"{x_col} Distribution (Box Plot)")

        elif chart_type == 'area':
            fig = px.area(df, x=x_col, y=y_col, title=f"{x_col} Area Chart")

        elif chart_type == 'heatmap':
            pivot_data = df.pivot_table(index=x_col, columns=y_col, aggfunc='size', fill_value=0)
            fig = px.imshow(pivot_data, title=f"{x_col} vs {y_col} Heatmap")

        else:
            return "<h4 style='color:red;'>Invalid chart type selected.</h4>"

        return f"<h5>Generated Chart:</h5>{fig.to_html(full_html=False)}<br><a href='/'>Go Back</a>"

    except Exception as e:
        return f"<h4 style='color:red;'>Error generating chart: {str(e)}</h4><br><a href='/'>Go Back</a>"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
