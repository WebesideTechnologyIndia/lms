# certificates/template_library.py

def get_template_library():
    """Pre-designed certificate templates"""
    
    return {
        'modern_blue': {
            'name': 'Modern Blue Certificate',
            'html': """
<div class="certificate modern-blue">
    <div class="border-frame">
        <div class="header">
            <div class="logo">
                <i class="fas fa-graduation-cap"></i>
            </div>
            <h1>Certificate of Completion</h1>
            <div class="decorative-line"></div>
        </div>
        
        <div class="content">
            <p class="subtitle">This is to certify that</p>
            <h2 class="student-name">{student_name}</h2>
            <p class="description">has successfully completed the course</p>
            <h3 class="course-name">{course_name}</h3>
            
            <div class="details">
                <div class="detail-item">
                    <span class="label">Batch:</span>
                    <span class="value">{batch_name}</span>
                </div>
                <div class="detail-item">
                    <span class="label">Completion Date:</span>
                    <span class="value">{completion_date}</span>
                </div>
                <div class="detail-item">
                    <span class="label">Certificate ID:</span>
                    <span class="value">{certificate_id}</span>
                </div>
                {% if grade %}
                <div class="detail-item">
                    <span class="label">Grade:</span>
                    <span class="value">{grade}</span>
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="footer">
            <div class="signature">
                <div class="signature-line"></div>
                <p class="signature-name">{instructor_name}</p>
                <p class="signature-title">Course Instructor</p>
            </div>
            <div class="seal">
                <div class="seal-circle">
                    <i class="fas fa-shield-alt"></i>
                    <p>VERIFIED</p>
                </div>
            </div>
        </div>
    </div>
</div>
            """,
            'css': """
body {
    margin: 0;
    padding: 40px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: 'Georgia', serif;
}

.certificate {
    max-width: 1000px;
    margin: 0 auto;
    background: white;
    position: relative;
}

.border-frame {
    border: 15px solid #667eea;
    padding: 50px;
    position: relative;
}

.border-frame::before {
    content: '';
    position: absolute;
    top: 30px;
    left: 30px;
    right: 30px;
    bottom: 30px;
    border: 2px solid #764ba2;
    pointer-events: none;
}

.header {
    text-align: center;
    margin-bottom: 40px;
}

.logo {
    width: 80px;
    height: 80px;
    margin: 0 auto 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 2.5rem;
}

h1 {
    color: #667eea;
    font-size: 3rem;
    margin: 20px 0 10px;
    font-weight: 700;
}

.decorative-line {
    width: 200px;
    height: 3px;
    background: linear-gradient(90deg, transparent, #764ba2, transparent);
    margin: 20px auto;
}

.content {
    text-align: center;
    margin-bottom: 50px;
}

.subtitle {
    font-size: 1.2rem;
    color: #666;
    margin-bottom: 10px;
}

.student-name {
    font-size: 2.5rem;
    color: #333;
    margin: 20px 0;
    font-weight: 700;
    border-bottom: 3px solid #667eea;
    display: inline-block;
    padding-bottom: 10px;
}

.description {
    font-size: 1.1rem;
    color: #666;
    margin: 20px 0 10px;
}

.course-name {
    font-size: 2rem;
    color: #764ba2;
    margin: 20px 0;
    font-weight: 600;
}

.details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    max-width: 600px;
    margin: 40px auto;
    text-align: left;
}

.detail-item {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}

.detail-item .label {
    font-weight: 600;
    color: #667eea;
    display: block;
    margin-bottom: 5px;
}

.detail-item .value {
    color: #333;
    font-size: 1.1rem;
}

.footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 60px;
}

.signature {
    flex: 1;
}

.signature-line {
    width: 250px;
    border-top: 2px solid #333;
    margin-bottom: 10px;
}

.signature-name {
    font-size: 1.2rem;
    font-weight: 600;
    margin: 5px 0;
    color: #333;
}

.signature-title {
    color: #666;
    font-size: 0.9rem;
    margin: 0;
}

.seal {
    flex: 0 0 auto;
}

.seal-circle {
    width: 120px;
    height: 120px;
    border: 5px solid #667eea;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
}

.seal-circle i {
    font-size: 2rem;
    color: #667eea;
    margin-bottom: 5px;
}

.seal-circle p {
    font-size: 0.8rem;
    font-weight: 700;
    color: #667eea;
    margin: 0;
}

@media print {
    body {
        background: white;
        padding: 0;
    }
}
            """
        },
        
        'classic_gold': {
            'name': 'Classic Gold Certificate',
            'html': """
<div class="certificate classic-gold">
    <div class="ornate-border">
        <div class="corner-ornament top-left"></div>
        <div class="corner-ornament top-right"></div>
        <div class="corner-ornament bottom-left"></div>
        <div class="corner-ornament bottom-right"></div>
        
        <div class="content-wrapper">
            <div class="header-section">
                <div class="emblem">★</div>
                <h1>Certificate of Achievement</h1>
                <div class="divider"></div>
            </div>
            
            <div class="main-content">
                <p class="presented-to">This certificate is proudly presented to</p>
                <h2 class="recipient-name">{student_name}</h2>
                
                <p class="recognition-text">
                    In recognition of successfully completing
                </p>
                
                <h3 class="course-title">{course_name}</h3>
                
                <div class="info-grid">
                    <div class="info-box">
                        <p class="info-label">Batch</p>
                        <p class="info-value">{batch_name}</p>
                    </div>
                    <div class="info-box">
                        <p class="info-label">Completed</p>
                        <p class="info-value">{completion_date}</p>
                    </div>
                    <div class="info-box">
                        <p class="info-label">Certificate ID</p>
                        <p class="info-value">{certificate_id}</p>
                    </div>
                    <div class="info-box">
                        <p class="info-label">Grade</p>
                        <p class="info-value">{grade}</p>
                    </div>
                </div>
            </div>
            
            <div class="signature-section">
                <div class="signature-block">
                    <div class="sig-line"></div>
                    <p class="sig-name">{instructor_name}</p>
                    <p class="sig-role">Course Instructor</p>
                </div>
                
                <div class="official-seal">
                    <div class="seal-inner">
                        <span class="seal-icon">✓</span>
                        <span class="seal-text">OFFICIAL</span>
                    </div>
                </div>
                
                <div class="signature-block">
                    <div class="sig-line"></div>
                    <p class="sig-name">Director</p>
                    <p class="sig-role">Academic Director</p>
                </div>
            </div>
        </div>
    </div>
</div>
            """,
            'css': """
body {
    margin: 0;
    padding: 30px;
    background: #1a1a1a;
    font-family: 'Garamond', 'Times New Roman', serif;
}

.certificate {
    max-width: 1100px;
    margin: 0 auto;
    background: linear-gradient(135deg, #f5f5dc 0%, #fffacd 100%);
}

.ornate-border {
    border: 20px solid;
    border-image: linear-gradient(45deg, #d4af37, #f4e5b8, #d4af37) 1;
    padding: 60px;
    position: relative;
    background: white;
}

.corner-ornament {
    position: absolute;
    width: 80px;
    height: 80px;
    background: radial-gradient(circle, #d4af37 0%, transparent 70%);
}

.corner-ornament::before {
    content: '❋';
    position: absolute;
    font-size: 3rem;
    color: #d4af37;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
}

.top-left { top: -10px; left: -10px; }
.top-right { top: -10px; right: -10px; }
.bottom-left { bottom: -10px; left: -10px; }
.bottom-right { bottom: -10px; right: -10px; }

.content-wrapper {
    border: 3px double #d4af37;
    padding: 50px;
}

.header-section {
    text-align: center;
    margin-bottom: 40px;
}

.emblem {
    font-size: 4rem;
    color: #d4af37;
    margin-bottom: 20px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}

h1 {
    font-size: 3.5rem;
    color: #2c1810;
    margin: 20px 0;
    font-weight: 700;
    letter-spacing: 3px;
}

.divider {
    width: 300px;
    height: 2px;
    background: linear-gradient(90deg, transparent, #d4af37, transparent);
    margin: 20px auto;
}

.main-content {
    text-align: center;
    margin: 40px 0;
}

.presented-to {
    font-size: 1.3rem;
    color: #555;
    font-style: italic;
    margin-bottom: 15px;
}

.recipient-name {
    font-size: 3rem;
    color: #2c1810;
    margin: 25px 0;
    font-weight: 700;
    text-decoration: underline;
    text-decoration-color: #d4af37;
    text-underline-offset: 8px;
}

.recognition-text {
    font-size: 1.2rem;
    color: #555;
    margin: 25px 0;
}

.course-title {
    font-size: 2.2rem;
    color: #8b4513;
    margin: 25px 0;
    font-weight: 600;
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin: 40px 0;
}

.info-box {
    background: linear-gradient(135deg, #fffacd, #f5f5dc);
    border: 2px solid #d4af37;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
}

.info-label {
    font-size: 0.9rem;
    color: #8b4513;
    font-weight: 600;
    margin-bottom: 5px;
    text-transform: uppercase;
}

.info-value {
    font-size: 1.1rem;
    color: #2c1810;
    font-weight: 700;
}

.signature-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: 60px;
    gap: 30px;
}

.signature-block {
    flex: 1;
    text-align: center;
}

.sig-line {
    width: 200px;
    border-top: 2px solid #2c1810;
    margin: 0 auto 10px;
}

.sig-name {
    font-size: 1.2rem;
    font-weight: 700;
    color: #2c1810;
    margin: 5px 0;
}

.sig-role {
    font-size: 0.9rem;
    color: #555;
    font-style: italic;
}

.official-seal {
    flex: 0 0 auto;
}

.seal-inner {
    width: 140px;
    height: 140px;
    border: 6px solid #d4af37;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #fffacd, #f5f5dc);
    box-shadow: 0 0 20px rgba(212, 175, 55, 0.3);
}

.seal-icon {
    font-size: 3rem;
    color: #d4af37;
    font-weight: 700;
}

.seal-text {
    font-size: 0.9rem;
    color: #8b4513;
    font-weight: 700;
    letter-spacing: 2px;
}

@media print {
    body {
        background: white;
        padding: 0;
    }
}
            """
        },
        
        'minimal_white': {
            'name': 'Minimal White Certificate',
            'html': """
<div class="certificate minimal-white">
    <div class="container">
        <div class="top-section">
            <div class="icon-badge">
                <svg viewBox="0 0 24 24" width="50" height="50">
                    <path fill="currentColor" d="M12,2L2,7V13C2,19.08 6.92,24 13,24C19.08,24 24,19.08 24,13V7L12,2M12,4.18L20,7.91V13C20,17.42 17.05,21.26 13,21.92V11H11V21.92C6.95,21.26 4,17.42 4,13V7.91L12,4.18Z"/>
                </svg>
            </div>
            <h1>Certificate</h1>
            <div class="thin-line"></div>
        </div>
        
        <div class="middle-section">
            <p class="intro-text">This certifies that</p>
            <h2 class="name">{student_name}</h2>
            <p class="completion-text">has successfully completed</p>
            <h3 class="course">{course_name}</h3>
            
            <div class="metadata">
                <div class="meta-item">
                    <span class="meta-key">Batch:</span>
                    <span class="meta-val">{batch_name}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-key">Date:</span>
                    <span class="meta-val">{completion_date}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-key">ID:</span>
                    <span class="meta-val">{certificate_id}</span>
                </div>
            </div>
        </div>
        
        <div class="bottom-section">
            <div class="auth-signature">
                <div class="line"></div>
                <p class="auth-name">{instructor_name}</p>
                <p class="auth-title">Authorized Signatory</p>
            </div>
        </div>
    </div>
</div>
            """,
            'css': """
body {
    margin: 0;
    padding: 50px;
    background: #f5f5f5;
    font-family: 'Helvetica Neue', 'Arial', sans-serif;
}

.certificate {
    max-width: 900px;
    margin: 0 auto;
    background: white;
    box-shadow: 0 10px 60px rgba(0,0,0,0.1);
}

.container {
    padding: 80px 100px;
}

.top-section {
    text-align: center;
    margin-bottom: 60px;
}

.icon-badge {
    width: 80px;
    height: 80px;
    margin: 0 auto 30px;
    color: #000;
    display: flex;
    align-items: center;
    justify-content: center;
}

h1 {
    font-size: 3rem;
    font-weight: 300;
    letter-spacing: 10px;
    text-transform: uppercase;
    color: #000;
    margin: 20px 0;
}

.thin-line {
    width: 80px;
    height: 1px;
    background: #000;
    margin: 30px auto;
}

.middle-section {
    text-align: center;
    margin: 60px 0;
}

.intro-text {
    font-size: 1.1rem;
    color: #666;
    margin-bottom: 20px;
    font-weight: 300;
}

.name {
    font-size: 2.5rem;
    font-weight: 400;
    color: #000;
    margin: 30px 0;
    position: relative;
    display: inline-block;
}

.name::after {
    content: '';
    position: absolute;
    bottom: -10px;
    left: 0;
    right: 0;
    height: 2px;
    background: #000;
}

.completion-text {
    font-size: 1rem;
    color: #666;
    margin: 30px 0 20px;
    font-weight: 300;
}

.course {
    font-size: 1.8rem;
    font-weight: 400;
    color: #333;
    margin: 20px 0 40px;
}

.metadata {
    display: flex;
    justify-content: center;
    gap: 40px;
    margin: 50px 0;
}

.meta-item {
    text-align: center;
}

.meta-key {
    display: block;
    font-size: 0.8rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 8px;
    font-weight: 500;
}

.meta-val {
    display: block;
    font-size: 1rem;
    color: #333;
    font-weight: 400;
}

.bottom-section {
    margin-top: 80px;
    display: flex;
    justify-content: center;
}

.auth-signature {
    text-align: center;
}

.line {
    width: 250px;
    border-top: 1px solid #000;
    margin-bottom: 15px;
}

.auth-name {
    font-size: 1.1rem;
    font-weight: 400;
    color: #000;
    margin: 10px 0 5px;
}

.auth-title {
    font-size: 0.9rem;
    color: #666;
    font-weight: 300;
    margin: 0;
}

@media print {
    body {
        background: white;
        padding: 0;
    }
    
    .certificate {
        box-shadow: none;
    }
}
            """
        }
    }