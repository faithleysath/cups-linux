import os
import subprocess
import cups
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

# 配置
UPLOAD_FOLDER = 'uploads'
# CUPS可以直接处理这些类型，只有Word文档需要转换
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt'}
CONVERTED_FOLDER = 'converted'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

# 确保上传和转换目录在应用启动时就存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(CONVERTED_FOLDER):
    os.makedirs(CONVERTED_FOLDER)

# --- 辅助函数 ---

def convert_if_needed(filepath, original_filename):
    """
    仅在需要时转换文件。目前只转换Word文档为PDF。
    其他格式（PDF, TXT, Images）由CUPS直接处理。
    """
    filename, ext = os.path.splitext(original_filename)
    ext = ext.lower()

    # 只有Word文档需要转换
    if ext not in ['.doc', '.docx']:
        return filepath

    pdf_path = os.path.join(app.config['CONVERTED_FOLDER'], filename + '.pdf')
    
    try:
        print(f"Converting Word document: {original_filename} to PDF...")
        subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', app.config['CONVERTED_FOLDER'], filepath],
            check=True,
            timeout=60  # 60秒超时
        )
        if os.path.exists(pdf_path):
            print("Conversion successful.")
            return pdf_path
        else:
            print("Conversion failed: PDF file not created.")
            return None
    except FileNotFoundError:
        print("ERROR: `libreoffice` command not found. Is it installed and in the system's PATH?")
        return None
    except subprocess.TimeoutExpired:
        print(f"ERROR: Timeout converting {original_filename}.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"ERROR: LibreOffice returned a non-zero exit code: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during conversion: {e}")
        return None


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

@app.route('/api/printers/<path:printer_name>/options')
def get_printer_options(printer_name):
    """获取指定打印机支持的选项"""
    try:
        conn = cups.Connection()
        attrs = conn.getPrinterAttributes(printer_name)
        
        options = {
            "media": attrs.get("media-supported", []),
            "quality": attrs.get("print-quality-supported", []),
            "sides": attrs.get("sides-supported", []),
            "color_mode": attrs.get("color-supported", [])
        }
        # 'print-quality-supported' 返回的是数字代码，需要映射
        quality_map = {3: 'draft', 4: 'normal', 5: 'high'}
        if options["quality"]:
            options["quality"] = [quality_map.get(q, 'unknown') for q in options["quality"]]

        return jsonify(options)
    except Exception as e:
        return jsonify({"error": f"无法获取打印机选项: {e}"}), 500


@app.route('/api/print', methods=['POST'])
def print_document():
    """处理文件上传和打印任务"""
    if 'file' not in request.files:
        return jsonify({"error": "没有文件部分"}), 400
    
    file = request.files['file']
    
    # 从表单中提取数据
    form_data = request.form
    printer_name = form_data.get('printer')
    copies = int(form_data.get('copies', 1))
    
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400
        
    if not printer_name:
        return jsonify({"error": "未选择打印机"}), 400

    if file:
        # 1. 安全地获取并验证文件扩展名
        _, file_extension = os.path.splitext(file.filename)
        file_extension = file_extension.lower()
        
        # 检查扩展名是否有效且在允许列表中
        if not file_extension or file_extension.strip('.') not in ALLOWED_EXTENSIONS:
            return jsonify({"error": "文件类型不支持"}), 400

        # 2. 生成唯一的、安全的文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{timestamp}_{unique_id}{file_extension}"
        
        # 3. 保存文件
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 4. 如果需要，转换文件
        printable_file_path = convert_if_needed(filepath, filename)
        
        if not printable_file_path:
            return jsonify({"error": "文件转换失败或格式不支持"}), 500

        # 提交到 CUPS 打印
        try:
            conn = cups.Connection()
            printers = conn.getPrinters()
            if printer_name not in printers:
                return jsonify({"error": "选择的打印机不存在"}), 400
            
            print_options = {'copies': str(copies)}
            
            # 动态添加其他从前端传来的打印选项
            for key, value in form_data.items():
                if key not in ['printer', 'copies']:
                    # CUPS选项名通常是kebab-case
                    option_key = key.replace('_', '-')
                    print_options[option_key] = value
            
            # 使用用户上传的原始文件名作为打印任务的标题，以优化体验
            job_title = file.filename
            job_id = conn.printFile(printer_name, printable_file_path, job_title, print_options)
            
            # 根据用户要求，不再自动清理文件
            # try:
            #     if os.path.exists(filepath):
            #         os.remove(filepath)
            #     if printable_file_path != filepath and os.path.exists(printable_file_path):
            #         os.remove(printable_file_path)
            # except Exception as e:
            #     print(f"Error cleaning up temporary files: {e}")

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
    app.run(host='0.0.0.0', port=5000, debug=True)
