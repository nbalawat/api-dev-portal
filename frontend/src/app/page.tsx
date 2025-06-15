'use client'

import { useState, useEffect } from 'react'
import { motion, useAnimation } from 'framer-motion'
import { ArrowRight, Shield, BarChart3, Users, Key, Zap, Globe, Lock } from 'lucide-react'

export default function HomePage() {
  const [isLoaded, setIsLoaded] = useState(false)
  const controls = useAnimation()

  useEffect(() => {
    setIsLoaded(true)
    controls.start('visible')
  }, [controls])

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        delayChildren: 0.3,
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.6,
        ease: "easeOut"
      }
    }
  }

  const features = [
    {
      icon: Key,
      title: "API Key Management",
      description: "Generate, manage, and monitor your API keys with advanced permissions and rate limiting.",
      gradient: "from-primary-500 to-primary-700",
      delay: 0
    },
    {
      icon: BarChart3,
      title: "Analytics Dashboard",
      description: "Real-time insights into API usage, performance metrics, and detailed reporting.",
      gradient: "from-success-500 to-success-700",
      delay: 0.1
    },
    {
      icon: Users,
      title: "User Management", 
      description: "Role-based access control with admin, developer, and viewer permissions.",
      gradient: "from-warning-500 to-warning-700",
      delay: 0.2
    },
    {
      icon: Shield,
      title: "Security First",
      description: "Enterprise security with JWT authentication, rate limiting, and audit logging.",
      gradient: "from-error-500 to-error-700",
      delay: 0.3
    }
  ]

  const stats = [
    { label: "API Endpoints", value: "70+", icon: Globe },
    { label: "Enterprise Security", value: "95.8%", icon: Lock },
    { label: "Test Coverage", value: "100%", icon: Shield },
    { label: "Response Time", value: "<100ms", icon: Zap }
  ]

  return (
    <div className="min-h-screen bg-mesh overflow-hidden selection-primary">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50/80 via-white to-purple-50/60" />
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-400/10 rounded-full blur-3xl animate-float" />
      <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-purple-400/10 rounded-full blur-3xl animate-float delay-1000" />
      
      {/* Navigation */}
      <motion.nav 
        className="nav-modern"
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <div className="flex items-center space-x-8">
          <div className="text-gradient font-bold text-lg">API Portal</div>
          <div className="hidden md:flex items-center space-x-6 text-sm">
            <a href="#features" className="text-gray-700 hover:text-blue-600 transition-colors font-medium">Features</a>
            <a href="#docs" className="text-gray-700 hover:text-blue-600 transition-colors font-medium">Docs</a>
            <a href="/login" className="text-gray-700 hover:text-blue-600 transition-colors font-medium">Sign In</a>
            <a href="/register" className="btn-enterprise">Get Started</a>
          </div>
        </div>
      </motion.nav>

      {/* Hero Section */}
      <motion.div 
        className="relative z-10 pt-24 pb-12 px-4"
        variants={containerVariants}
        initial="hidden"
        animate={controls}
      >
        <div className="max-w-6xl mx-auto text-center">
          <motion.div variants={itemVariants}>
            <motion.h1 
              className="text-gradient text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6"
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              API Developer Portal
            </motion.h1>
          </motion.div>

          <motion.div variants={itemVariants}>
            <p className="text-lg md:text-xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
              Enterprise-grade API management with 
              <span className="text-blue-600 font-semibold"> authentication</span>, 
              <span className="text-blue-600 font-semibold"> analytics</span>, and 
              <span className="text-blue-600 font-semibold"> comprehensive documentation</span>.
            </p>
          </motion.div>

          <motion.div 
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12"
            variants={itemVariants}
          >
            <motion.a 
              href="/register" 
              className="btn-enterprise group inline-flex items-center text-lg"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Get Started
              <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </motion.a>
            <motion.a 
              href="/api/docs" 
              className="btn-secondary group inline-flex items-center text-lg"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              View API Docs
              <Globe className="ml-2 w-5 h-5 group-hover:rotate-12 transition-transform" />
            </motion.a>
          </motion.div>

          {/* Stats Section */}
          <motion.div 
            className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12"
            variants={itemVariants}
          >
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                className="glass-card text-center"
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.5 + index * 0.1, duration: 0.6 }}
                whileHover={{ y: -5 }}
              >
                <stat.icon className="w-8 h-8 mx-auto mb-3 text-primary-600" />
                <div className="text-2xl font-bold text-gradient mb-1">{stat.value}</div>
                <div className="text-sm text-slate-600">{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.div>

      {/* Features Section */}
      <motion.section 
        id="features"
        className="relative z-10 py-12 px-4"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
        viewport={{ once: true }}
      >
        <div className="max-w-6xl mx-auto">
          <motion.div 
            className="text-center mb-10"
            initial={{ y: 30, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              Enterprise Features
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Comprehensive API management platform designed for modern enterprises
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                className="card-glass group cursor-pointer"
                initial={{ y: 50, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ delay: feature.delay, duration: 0.6 }}
                viewport={{ once: true }}
                whileHover={{ y: -10, scale: 1.02 }}
              >
                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900 mb-3 group-hover:text-primary-600 transition-colors">
                  {feature.title}
                </h3>
                <p className="text-slate-600 leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.section>

      {/* CTA Section */}
      <motion.section 
        className="relative z-10 py-20 px-4"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
        viewport={{ once: true }}
      >
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            className="glass-card"
            initial={{ scale: 0.9, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-6">
              Ready to Get Started?
            </h2>
            <p className="text-lg text-slate-600 mb-8 max-w-2xl mx-auto">
              Join thousands of developers using our enterprise API platform for their mission-critical applications.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <motion.a 
                href="/dashboard" 
                className="btn-enterprise group"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Start Building
                <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </motion.a>
              <motion.a 
                href="/auth/register" 
                className="btn-secondary"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Create Account
              </motion.a>
            </div>

            <div className="mt-8 flex items-center justify-center space-x-4 text-sm text-slate-500">
              <div className="flex items-center">
                <div className="status-online mr-2" />
                <span>System Online</span>
              </div>
              <div className="w-1 h-1 bg-slate-300 rounded-full" />
              <span>99.9% Uptime</span>
              <div className="w-1 h-1 bg-slate-300 rounded-full" />
              <span>24/7 Support</span>
            </div>
          </motion.div>
        </div>
      </motion.section>

      {/* Footer */}
      <motion.footer 
        className="relative z-10 py-12 px-4 border-t border-slate-200/50"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
      >
        <div className="max-w-7xl mx-auto text-center">
          <div className="text-gradient font-bold text-xl mb-4">API Developer Portal</div>
          <p className="text-slate-600 mb-6">
            Enterprise-grade API management platform for modern developers
          </p>
          <div className="flex items-center justify-center space-x-8 text-sm text-slate-500">
            <a href="/docs" className="hover:text-primary-600 transition-colors">Documentation</a>
            <a href="/support" className="hover:text-primary-600 transition-colors">Support</a>
            <a href="/status" className="hover:text-primary-600 transition-colors">Status</a>
            <a href="/privacy" className="hover:text-primary-600 transition-colors">Privacy</a>
          </div>
        </div>
      </motion.footer>
    </div>
  )
}