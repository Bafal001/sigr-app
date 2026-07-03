/**
 * SIGR — Scripts principaux
 * Utilitaires communs à toutes les pages.
 */

// Détection du support Drag & Drop
(function () {
    'use strict';

    // Fonction utilitaire : formater la taille d'un fichier
    window.formatFileSize = function (bytes) {
        if (bytes === 0) return '0 o';
        if (bytes < 1024) return bytes + ' o';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' Ko';
        return (bytes / 1048576).toFixed(1) + ' Mo';
    };

    // Fonction utilitaire : afficher une notification toast
    window.showToast = function (message, type = 'info') {
        const colors = {
            success: '#27ae60',
            error: '#e74c3c',
            info: '#2980b9',
            warning: '#f39c12',
        };
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            info: 'info-circle',
            warning: 'exclamation-triangle',
        };
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: ${colors[type] || colors.info};
            color: #fff;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
            z-index: 9999;
            font-size: 0.9rem;
            animation: fadeInUp 0.3s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        `;
        toast.innerHTML = `<i class="bi bi-${icons[type]}"></i> ${message}`;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    };

    // Ajouter le keyframe d'animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to   { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(style);

    console.log('✅ SIGR — Scripts initialisés');
})();
