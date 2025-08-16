# HR Management System

A modern, responsive HR Management System built with React, TypeScript, Tailwind CSS, and Framer Motion.

## 🚀 Quick Start

1. Make sure you have Node.js installed (version 14 or higher)
2. Run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
3. Navigate to the project:
   ```bash
   cd hr-management-system
   ```
4. Start the development server:
   ```bash
   npm start
   ```

## ✅ What's Fixed in This Version

This script addresses the compilation issues:

1. **✅ PostCSS Configuration**: Updated to use the correct Tailwind CSS setup
2. **✅ Removed Unused Imports**: Fixed the Filter import warning
3. **✅ Dependencies**: Using compatible versions of all packages
4. **✅ TypeScript**: Proper TypeScript configuration

## 🎨 Features

### Three Main Sections (Sidebar Navigation)
- **📊 Dashboard**: Statistics overview with animated cards
- **💼 Career Portal**: Job listings and posting functionality  
- **📋 Application Status**: Application management and tracking

### Visual Features
- **Glass morphism effects** with backdrop blur
- **Gradient backgrounds** that shift and animate
- **Smooth hover effects** on all interactive elements
- **Floating animations** for cards and elements
- **Slide-in animations** for page transitions
- **Professional sidebar** with animated navigation
- **Pulse effects** for notifications and status indicators

### Role-Based Access
- **HR Manager**: Post jobs, manage applications, hire/reject candidates
- **Employee**: Browse jobs, apply for positions, track applications

## 🛠 Technologies Used

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **Lucide React** for icons
- **PostCSS** for CSS processing

## 📂 Project Structure

```
hr-management-system/
├── src/
│   ├── components/
│   │   ├── Layout.tsx          # Main layout wrapper
│   │   ├── Sidebar.tsx         # Animated sidebar navigation
│   │   ├── Dashboard.tsx       # Dashboard with statistics
│   │   ├── CareerPortal.tsx    # Job listings and posting
│   │   └── ApplicationStatus.tsx # Application management
│   ├── App.tsx                 # Main app component
│   └── index.css              # Global styles with animations
├── tailwind.config.js          # Tailwind configuration
├── postcss.config.js           # PostCSS configuration
└── package.json               # Dependencies
```

## 🎯 Key Components

### Dashboard
- Animated statistics cards showing job counts, applications, hired candidates
- Recent applications and active jobs widgets
- Gradient cards with hover effects and floating animations

### Career Portal
- Job search and filtering
- Job posting forms (HR only)
- Application submission (Employees)
- Job detail modals with smooth animations

### Application Status
- Comprehensive application table
- Status management with visual indicators
- Candidate detail modals
- Action buttons for HR (interview, hire, reject)

## 🎨 Animation Features

- **Stagger animations** for list items
- **Scale animations** on hover
- **Slide transitions** between pages
- **Modal animations** with backdrop blur
- **Floating effects** for interactive elements
- **Pulse animations** for notifications
- **Gradient shifts** in backgrounds

## 🔧 Customization

### Colors
Edit `tailwind.config.js` to customize the color scheme:
```javascript
colors: {
  primary: {
    // Your custom colors
  }
}
```

### Animations
Modify animation timings in `src/index.css`:
```css
.floating {
  animation: float 6s ease-in-out infinite;
}
```

## 🚀 Deployment

1. Build the project:
   ```bash
   npm run build
   ```

2. Deploy the `build` folder to your hosting service:
   - **Netlify**: Drag and drop the build folder
   - **Vercel**: Connect your repository
   - **AWS S3**: Upload to S3 bucket with static hosting

## 🔍 Troubleshooting

### Common Issues

1. **PostCSS Error**: 
   - Make sure you're using the latest version
   - Delete `node_modules` and run `npm install` again

2. **TypeScript Errors**:
   - Ensure all imports are correct
   - Check that all dependencies are installed

3. **Styling Issues**:
   - Verify Tailwind CSS is properly configured
   - Check that `@tailwind` directives are in `index.css`

## 📱 Responsive Design

The application is fully responsive and works on:
- **Desktop** (1200px+)
- **Tablet** (768px - 1199px)
- **Mobile** (320px - 767px)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Ensure all dependencies are properly installed
3. Try deleting `node_modules` and running `npm install` again
4. Check that Node.js version is 14 or higher

## 🎉 What You Get

After running this script, you'll have:
- ✅ A fully functional HR management system
- ✅ Beautiful animations and transitions
- ✅ Professional UI with glass morphism effects
- ✅ Role-based access control
- ✅ Responsive design for all devices
- ✅ TypeScript support for better development
- ✅ Modern React patterns and best practices

---

**Happy coding! 🚀**
