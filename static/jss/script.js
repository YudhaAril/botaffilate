// script.js

// Toast Notification System
function showToast(message, type = 'info', duration = 3000) {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.custom-toast');
    existingToasts.forEach(toast => toast.remove());

    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }

    // Create toast
    const toast = document.createElement('div');
    toast.className = `custom-toast toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, {
        animation: true,
        autohide: true,
        delay: duration
    });
    bsToast.show();

    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
        if (toastContainer.children.length === 0) {
            toastContainer.remove();
        }
    });
}

// Confirm Dialog
function confirmAction(message, callback) {
    if (confirm(message)) {
        if (typeof callback === 'function') {
            callback();
        }
        return true;
    }
    return false;
}

// Form Validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Auto-resize Textarea
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Copy to Clipboard
function copyToClipboard(text, successMessage = 'Berhasil disalin!') {
    navigator.clipboard.writeText(text).then(() => {
        showToast(successMessage, 'success');
    }).catch(err => {
        console.error('Gagal menyalin: ', err);
        showToast('Gagal menyalin teks', 'error');
    });
}

// Format Date
function formatDate(date, format = 'id-ID') {
    const d = new Date(date);
    return d.toLocaleDateString(format, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Debounce Function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Loading State
function setLoading(element, isLoading) {
    if (isLoading) {
        element.disabled = true;
        const originalText = element.innerHTML;
        element.setAttribute('data-original-text', originalText);
        element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    } else {
        element.disabled = false;
        const originalText = element.getAttribute('data-original-text');
        if (originalText) {
            element.innerHTML = originalText;
        }
    }
}

// Search Functionality
function performSearch(query, endpoint = '/search') {
    if (!query.trim()) {
        showToast('Masukkan kata kunci untuk mencari', 'warning');
        return;
    }

    window.location.href = `${endpoint}?q=${encodeURIComponent(query)}`;
}

// Modal Helper
function showModal(modalId) {
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}

function hideModal(modalId) {
    const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
    if (modal) {
        modal.hide();
    }
}

// AJAX Helper
function ajaxRequest(url, method = 'GET', data = null, callback = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }

    return fetch(url, options)
        .then(response => response.json())
        .then(data => {
            if (callback) callback(data);
            return data;
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Terjadi kesalahan', 'error');
        });
}

// Character Counter
function setupCharCounter(textareaId, counterId, maxLength = null) {
    const textarea = document.getElementById(textareaId);
    const counter = document.getElementById(counterId);

    if (!textarea || !counter) return;

    function updateCounter() {
        const count = textarea.value.length;
        counter.textContent = `${count} karakter`;
        
        if (maxLength) {
            const percentage = (count / maxLength) * 100;
            if (percentage > 90) {
                counter.classList.add('text-danger');
            } else if (percentage > 75) {
                counter.classList.add('text-warning');
            } else {
                counter.classList.remove('text-danger', 'text-warning');
            }
        }
    }

    textarea.addEventListener('input', updateCounter);
    updateCounter(); // Initial count
}

// Table Row Actions
function setupTableActions() {
    // Delete confirmation
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            const message = this.getAttribute('data-confirm') || 'Apakah Anda yakin ingin menghapus?';
            
            if (confirmAction(message, () => {
                window.location.href = url;
            }));
        });
    });

    // Row selection
    document.querySelectorAll('.table-selectable tbody tr').forEach(row => {
        row.addEventListener('click', function() {
            this.classList.toggle('table-active');
        });
    });
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-resize textareas
    document.querySelectorAll('textarea[data-autoresize]').forEach(textarea => {
        textarea.addEventListener('input', function() {
            autoResizeTextarea(this);
        });
        autoResizeTextarea(textarea); // Initial resize
    });

    // Setup form validation
    document.querySelectorAll('form[data-validate]').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this.id)) {
                e.preventDefault();
                showToast('Harap isi semua field yang wajib diisi', 'warning');
            }
        });
    });

    // Setup table actions
    setupTableActions();

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[type="search"], input[name="q"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        // Escape to close modals
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                modal.hide();
            }
        }

        // Ctrl/Cmd + Enter to submit forms
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const focusedElement = document.activeElement;
            if (focusedElement && focusedElement.tagName === 'TEXTAREA') {
                const form = focusedElement.closest('form');
                if (form && !form.classList.contains('prevent-ctrl-enter')) {
                    e.preventDefault();
                    form.submit();
                }
            }
        }
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Lazy loading images
    if ('IntersectionObserver' in window) {
        const lazyImages = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });
        lazyImages.forEach(img => imageObserver.observe(img));
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
});

// Export functions for use in other scripts
window.AppUtils = {
    showToast,
    confirmAction,
    validateForm,
    autoResizeTextarea,
    copyToClipboard,
    formatDate,
    debounce,
    setLoading,
    performSearch,
    showModal,
    hideModal,
    ajaxRequest,
    setupCharCounter
};