import os
import subprocess
import cups
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image

# 配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'}
CONVERTED_FOLDER = 'uploads' # 转换后的文件也保存在此

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

# --- 辅助函数 ---

def allowed_file(filename):
    """检查文件扩展名是否在允许范围内"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_to_pdf(filepath, original_filename):
    """
    将各种格式的文件转换为PDF，以便CUPS处理。
    - DOC/DOCX: 使用LibreOffice
    - Images: 使用Pillow
    """
    filename, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    pdf_path = os.path.join(app.config['CONVERTED_FOLDER'], filename + '.pdf')

    if ext == '.pdf':
        return filepath

    try:
        if ext in ['.doc', '.docx']:
            print(f"Converting Word document: {original_filename}")
            subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', app.config['CONVERTED_FOLDER'], filepath],
                check=True, timeout=60 # 60秒超时
            )
            if os.path.exists(pdf_path):
                return pdf_path
            else:
                print("Conversion failed: PDF file not found after LibreOffice execution.")
                return None
        
        elif ext in ['.jpg', '.jpeg', '.png']:
            print(f"Converting image: {original_filename}")
            with Image.open(filepath) as img:
                # 确保图像是RGB模式，以避免某些PNG格式的问题
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img.save(pdf_path, 'PDF', resolution=100.0)
            return pdf_path
            
        elif ext == '.txt':
             print(f"Converting text file: {original_filename}")
             # 简单的文本转PDF可以通过CUPS的texttopdf过滤器，但这里我们手动创建
             # 为了简单起见，我们用一个外部工具，或者可以自己画一个PDF
             # 这里我们还是依赖cups的内置能力，直接打印txt
             return filepath

    except FileNotFoundError:
        print("ERROR: `libreoffice` command not found. Please install it (`sudo apt-get install libreoffice`).")
        return None
    except subprocess.TimeoutExpired:
        print(f"ERROR: Timeout converting {original_filename}. The file might be too large or complex.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during conversion: {e}")
        return None
        
    return None # 如果没有匹配的转换规则


# --- API 路由 ---

@app.route('/')
def index():
    """渲染主页面"""
    return render_template('index.html')

@app.route('/api/printers')
def get_printers():
    """获取 CUPS 配置的打印机列表"""
    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
        return jsonify(list(printers.keys()))
    except Exception as e:
        return jsonify({"error": f"无法连接到 CUPS 服务: {e}"}), 500

@app.route('/api/print', methods=['POST'])
def print_document():
    """处理文件上传和打印任务"""
    if 'file' not in request.files:
        return jsonify({"error": "没有文件部分"}), 400
    
    file = request.files['file']
    printer_name = request.form.get('printer')
    copies = int(request.form.get('copies', 1))
    
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400
        
    if not printer_name:
        return jsonify({"error": "未选择打印机"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 转换文件为 PDF (如果需要)
        printable_file_path = convert_to_pdf(filepath, filename)
        
        if not printable_file_path:
            return jsonify({"error": "文件转换失败"}), 500

        # 提交到 CUPS 打印
        try:
            conn = cups.Connection()
            printers = conn.getPrinters()
            if printer_name not in printers:
                return jsonify({"error": "选择的打印机不存在"}), 400
            
            print_options = {
                'copies': str(copies)
                # 其他打印选项可以在这里添加, e.g., 'media': 'A4', 'color-mode': 'monochrome'
            }
            
            job_id = conn.printFile(printer_name, printable_file_path, "Web Print Job", print_options)
            
            # 打印后可以考虑删除临时文件
            # os.remove(filepath)
            # if printable_file_path != filepath:
            #     os.remove(printable_file_path)

            return jsonify({"success": True, "job_id": job_id})
            
        except Exception as e:
            return jsonify({"error": f"打印失败: {e}"}), 500
    
    return jsonify({"error": "文件类型不支持"}), 400

@app.route('/api/jobs/<int:job_id>')
def get_job_status(job_id):
    """查询打印任务的状态"""
    try:
        conn = cups.Connection()
        job = conn.getJobAttributes(job_id)
        # 简化状态信息
        status_map = {
            3: 'pending',
            4: 'pending_held',
            5: 'processing',
            6: 'stopped',
            7: 'canceled',
            8: 'aborted',
            9: 'completed'
        }
        state = job.get('job-state')
        state_reason = job.get('job-state-reasons')
        return jsonify({
            "job_id": job_id,
            "state": status_map.get(state, 'unknown'),
            "reason": state_reason
        })
    except Exception as e:
        return jsonify({"error": f"无法获取任务状态: {e}"}), 500

# --- 静态文件服务 (用于 CSS/JS) ---
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host='0.0.0.0', port=5000, debug=True)
