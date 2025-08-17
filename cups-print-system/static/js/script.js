document.addEventListener('DOMContentLoaded', function() {
    const printerSelect = document.getElementById('printer');
    const printForm = document.getElementById('printForm');
    const statusDiv = document.getElementById('status');
    const submitBtn = document.getElementById('submitBtn');

    // 1. 获取并填充打印机列表
    fetch('/api/printers')
        .then(response => response.json())
        .then(printers => {
            printerSelect.innerHTML = '<option value="">-- 请选择一台打印机 --</option>';
            if (printers && printers.length > 0) {
                printers.forEach(printer => {
                    const option = document.createElement('option');
                    option.value = printer;
                    option.textContent = printer;
                    printerSelect.appendChild(option);
                });
            } else {
                printerSelect.innerHTML = '<option value="">未找到可用打印机</option>';
                showStatus('未找到可用打印机或无法连接 CUPS 服务。', 'error');
            }
        })
        .catch(error => {
            console.error('Error fetching printers:', error);
            printerSelect.innerHTML = '<option value="">加载打印机失败</option>';
            showStatus('加载打印机列表失败，请检查后端服务是否正常。', 'error');
        });

    // 2. 处理表单提交
    printForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const formData = new FormData(printForm);
        const fileInput = document.getElementById('file');

        if (!fileInput.files || fileInput.files.length === 0) {
            showStatus('请选择一个文件。', 'error');
            return;
        }
        
        if (!printerSelect.value) {
            showStatus('请选择一台打印机。', 'error');
            return;
        }

        showStatus('正在上传并提交任务...', 'info');
        submitBtn.disabled = true;
        submitBtn.textContent = '正在提交...';

        fetch('/api/print', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showStatus(`打印任务已成功提交！任务 ID: ${data.job_id}`, 'success');
                pollJobStatus(data.job_id);
            } else {
                showStatus(`错误: ${data.error}`, 'error');
                resetForm();
            }
        })
        .catch(error => {
            console.error('Error submitting print job:', error);
            showStatus('提交打印任务失败，请检查网络或服务器状态。', 'error');
            resetForm();
        });
    });

    // 3. 轮询任务状态
    function pollJobStatus(jobId) {
        const interval = setInterval(() => {
            fetch(`/api/jobs/${jobId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showStatus(`查询任务 ${jobId} 状态失败: ${data.error}`, 'error');
                        clearInterval(interval);
                        resetForm();
                        return;
                    }
                    
                    const statusMsg = `任务 ${jobId} 状态: ${data.state} (${data.reason || '无信息'})`;
                    showStatus(statusMsg, 'info');

                    if (['completed', 'canceled', 'aborted'].includes(data.state)) {
                        clearInterval(interval);
                        if(data.state === 'completed') {
                            showStatus(`任务 ${jobId} 已完成！`, 'success');
                        } else {
                            showStatus(`任务 ${jobId} 已结束，状态: ${data.state}`, 'error');
                        }
                        resetForm();
                    }
                })
                .catch(err => {
                    showStatus(`查询任务 ${jobId} 状态时发生网络错误。`, 'error');
                    clearInterval(interval);
                    resetForm();
                });
        }, 3000); // 每 3 秒查询一次
    }

    // 显示状态消息
    function showStatus(message, type) {
        statusDiv.textContent = message;
        statusDiv.className = `status-container ${type}`;
    }
    
    // 重置表单状态
    function resetForm() {
        submitBtn.disabled = false;
        submitBtn.textContent = '提交打印';
        printForm.reset();
    }
});
