#!/usr/bin/env python
# Script to fix indentation in auth.py

def main():
    input_file = 'app/routes/auth.py'
    
    # Read the file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix the specific indentation issues
    # Fix in login function - Redirect based on role
    for i in range(len(lines)):
        # Look for the section with "Redirect based on role"
        if "# Redirect based on role" in lines[i]:
            # Fix the indentation for the next few lines
            if i + 1 < len(lines) and "if user.role == 'admin':" in lines[i+1]:
                lines[i+1] = "        if user.role == 'admin':\n"
                if i + 2 < len(lines) and "next_page = url_for('admin.dashboard')" in lines[i+2]:
                    lines[i+2] = "            next_page = url_for('admin.dashboard')\n"
                if i + 3 < len(lines) and "elif user.role == 'official'" in lines[i+3]:
                    lines[i+3] = "        elif user.role == 'official' and form.department.data:\n"
                if i + 4 < len(lines) and "session['department'] = form.department.data" in lines[i+4]:
                    lines[i+4] = "            session['department'] = form.department.data\n"
                if i + 5 < len(lines) and "next_page = url_for('admin.dashboard')" in lines[i+5]:
                    lines[i+5] = "            next_page = url_for('admin.dashboard')\n"
    
    # Fix in logout function
    for i in range(len(lines)):
        if "uid=current_user.uid," in lines[i] and "action='logout'," in lines[i+1]:
            lines[i] = "                uid=current_user.uid,\n"
            lines[i+1] = "                action='logout',\n"
            lines[i+2] = "                resource_type='user',\n"
            lines[i+3] = "                resource_id=current_user.uid,\n"
            lines[i+4] = "                details='User logged out',\n"
            lines[i+5] = "                ip_address=request.remote_addr\n"
    
    # Fix in register function - create_user parameters
    for i in range(len(lines)):
        if "user = firebase_auth.create_user(" in lines[i]:
            lines[i+1] = "                email=form.email.data,\n"
            lines[i+2] = "                password=form.password.data,\n"
            lines[i+3] = "                display_name=display_name,\n"
            lines[i+4] = "                phone_number=form.phone.data if form.phone.data and form.phone.data.startswith('+') else None,\n"
            lines[i+5] = "                role='citizen'  # Always start as citizen for security\n"
            lines[i+6] = "            )\n"
    
    # Fix in reset_password_request function
    for i in range(len(lines)):
        if "if user:" in lines[i] and "# Send password reset email" in lines[i+1]:
            # Fix these lines and the following audit log call
            lines[i] = "                if user:\n"
            # The following 6-7 lines should be properly indented
            for j in range(i+1, i+10):
                if "firebase_auth.create_audit_log(" in lines[j]:
                    # Fix audit log indentation
                    for k in range(j, j+8):
                        if k < len(lines):
                            # Add proper indentation
                            if "uid=user.uid," in lines[k]:
                                lines[k] = "                        uid=user.uid,\n"
                            elif "action=" in lines[k]:
                                lines[k] = "                        action='password_reset_request',\n"
                            elif "resource_type=" in lines[k]:
                                lines[k] = "                        resource_type='user',\n"
                            elif "resource_id=" in lines[k]:
                                lines[k] = "                        resource_id=user.uid,\n"
                            elif "details=" in lines[k]:
                                lines[k] = "                        details='Password reset requested',\n"
                            elif "ip_address=" in lines[k]:
                                lines[k] = "                        ip_address=request.remote_addr\n"
    
    # Fix in reset_password function
    for i in range(len(lines)):
        if "return redirect(url_for('auth.login'))" in lines[i] and "def reset_password" in lines[i-5]:
            lines[i] = "    return redirect(url_for('auth.login'))\n"
    
    # Write the fixed content back to the file
    with open(input_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Fixed indentation issues in {input_file}")

if __name__ == "__main__":
    main() 