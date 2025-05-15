from flask import Flask, render_template_string, request
import pandas as pd
import plotly.express as px
import os
import chardet

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
        .btn- { background-color: #ffc72c; color: black; font-weight: bold; }
        .-logo { width: 150px; margin-bottom: 20px; }
        footer { margin-top: 20px; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
<div class="container text-center">
    <img src="https://d1csarkz8obe9u.cloudfront.net/posterpreviews/alphabet-logo-brand-logo-modern-logo-company-design-template-5286d82273e1863d743f912089beaa62_screen.jpg?ts=1704789071" class="-logo" alt="Logo">
    <h3 class="mt-3">Anomaly Detection & Insights Dashboard</h3>
    <form action="/upload" method="post" enctype="multipart/form-data" class="mb-4">
        <input type="file" name="file" class="form-control mb-2" required>
        <button type="submit" class="btn btn-">Upload & Analyze</button>
    </form>
    {{ analysis|safe }}
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
    if not file:
        return "<h4 style='color:red;'>No file uploaded.</h4>"

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Detecting file encoding to prevent UTF-8 errors
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']

    try:
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file_path, engine='openpyxl')
        else:
            df = pd.read_csv(file_path, encoding=encoding, errors='replace')
    except Exception as e:
        return f"<h4 style='color:red;'>Error reading file: {e}</h4>"

    if df.empty:
        return "<h4 style='color:red;'>Uploaded file has no data.</h4>"

    # Missing Values
    missing_values = df.isnull().sum().reset_index()
    missing_values.columns = ['Column', 'Missing Values']
    missing_values = missing_values[missing_values['Missing Values'] > 0]

    # Error Patterns
    error_patterns = []
    for col in df.columns:
        for err in ['#REF!', '#N/A', '#DIV/0!', '#VALUE!']:
            count = df[col].astype(str).str.contains(err, na=False).sum()
            if count > 0:
                error_patterns.append([err, col, count])

    error_df = pd.DataFrame(error_patterns, columns=['Error Type', 'Column', 'Count'])

    # Category Insights
    category_insights = "<h5>Category Insights:</h5>"
    for col in df.select_dtypes(include=['object']).columns:
        count_data = df[col].value_counts().nlargest(10).reset_index()
        count_data.columns = ['Value', 'Count']
        if len(count_data) > 0:
            category_insights += f"<h6>{col} (Total: {df[col].count()})</h6>{count_data.to_html(classes='table table-bordered table-sm')}"

    summary_html = f'''
    <h5>Summary</h5>
    <h5>Missing Values:</h5>{missing_values.to_html(classes='table table-bordered', index=False) if not missing_values.empty else "<p>No Missing Values</p>"}
    <h5>Error Patterns:</h5>{error_df.to_html(classes='table table-bordered', index=False) if not error_df.empty else "<p>No Error Patterns Detected.</p>"}
    {category_insights}
    <form method='post' action='/visualize'>
        <select name='column' multiple class="form-control mt-2">
            {''.join([f"<option value='{col}'>{col}</option>" for col in df.columns])}
        </select>
        <select name='chart_type' class="form-control mt-2">
            <option value='bar'>Bar Chart</option>
            <option value='pie'>Pie Chart</option>
            <option value='line'>Line Chart</option>
            <option value='histogram'>Histogram</option>
        </select>
        <button type='submit' class='btn btn- mt-3'>Generate Charts</button>
    </form>
    '''

    return render_template_string(HTML_TEMPLATE, analysis=summary_html)

@app.route('/visualize', methods=['POST'])
def visualize():
    try:
        file_path = os.path.join(UPLOAD_FOLDER, 'uploaded_data.csv')
        df = pd.read_csv(file_path)
        columns = request.form.getlist('column')
        chart_type = request.form.get('chart_type')

        charts_html = ""
        for col in columns:
            if col in df.columns:
                if chart_type == 'pie':
                    fig = px.pie(df, names=col)
                elif chart_type == 'bar':
                    fig = px.bar(df, x=col, y=df[col].value_counts().values)
                elif chart_type == 'histogram':
                    fig = px.histogram(df, x=col)
                else:
                    fig = px.line(df, x=df.index, y=col)
                charts_html += fig.to_html(full_html=False)

        return f"<h5>Selected Charts:</h5>{charts_html}<br><a href='/'>Go Back</a>"

    except Exception as e:
        return f"<h4 style='color:red;'>Error generating chart: {str(e)}</h4><br><a href='/'>Go Back</a>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
