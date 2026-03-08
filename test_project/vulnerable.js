// Vulnerable JavaScript file
function insecureFunction() {
    // DOM XSS vulnerability
    document.getElementById('content').innerHTML = userInput;
    
    // eval() vulnerability
    eval("console.log('bad')");
    
    // Hardcoded API key
    const SOME_API_KEY = "sk_live_1234567890abcdefghijklmn";
    
    // JWT token
    const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
}

const i = {
    WEB_API_KEY:"CcLgB6MRrQJCcJGxmZTB2XsPSJiZS8Aicbt2k9m4or77b2y4"
}