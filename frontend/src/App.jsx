import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const [loading, setLoading] = useState(true)
  // Отдельные категории для каждого типа боли
  const [personalCategories, setPersonalCategories] = useState([])   // Категории для личных болей
  const [corporateCategories, setCorporateCategories] = useState([]) // Категории для корпоративных болей
  const [selectedSection, setSelectedSection] = useState(null)
  const [allPlans, setAllPlans] = useState([])
  const [modalData, setModalData] = useState(null)
  const [tooltip, setTooltip] = useState({ show: false, text: '', x: 0, y: 0 })
  const [showAdvantages, setShowAdvantages] = useState(true)
  const [showQuestions, setShowQuestions] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [loginError, setLoginError] = useState('')
  const [showRegister, setShowRegister] = useState(false)
  const [registerData, setRegisterData] = useState({ username: '', email: '', password: '', full_name: '', role: 'user' })
  const [registerError, setRegisterError] = useState('')
  
  // Состояния для администратора
  const [showUserManagement, setShowUserManagement] = useState(false)
  const [users, setUsers] = useState([])
  const [editingInModal, setEditingInModal] = useState(false)
  const [modalEditValues, setModalEditValues] = useState({})
  
  // Состояния для управления разделами
  const [showSectionManagement, setShowSectionManagement] = useState(false)
  const [sections, setSections] = useState([])
  const [newSectionName, setNewSectionName] = useState('')
  const [selectedSectionForEdit, setSelectedSectionForEdit] = useState(null)
  const [showAddCharacteristic, setShowAddCharacteristic] = useState(false)
  const [newCharacteristic, setNewCharacteristic] = useState({
    name: '',
    standard: '',
    expert: '',
    optimal: '',
    express: '',
    ultra: '',
    advantages: '',
    questions: '',
    personal_pain: '',
    corporate_pain: ''
  })
  const [sectionCharacteristics, setSectionCharacteristics] = useState([])
  const [draggedChar, setDraggedChar] = useState(null)
  const [dragOverChar, setDragOverChar] = useState(null)

  const categories = ['Легкость', 'Безопасность', 'Экономия', 'Скорость']

  const categoryTooltips = {
    'Легкость': 'Упрощение процессов и снижение сложности работы',
    'Безопасность': 'Защита данных и соответствие требованиям',
    'Экономия': 'Оптимизация затрат и эффективность расходов',
    'Скорость': 'Быстрое выполнение задач и сокращение сроков'
  }

  // Маппинг категорий в короткие буквы
  const categoryShortNames = {
    'Легкость': 'Л',
    'Безопасность': 'Б',
    'Экономия': 'Э',
    'Скорость': 'С'
  }

  // Функция для получения короткого названия категории
  const getCategoryShort = (category) => {
    const normalized = category.trim()
      .replace('Лёгкость', 'Легкость')
      .replace('Лекость', 'Легкость')
      .replace('Безопасностьасность', 'Безопасность')
      .replace('Безопастность', 'Безопасность')
      .replace('Безоп', 'Безопасность')
      .replace('Эконом', 'Экономия')
      .replace('Сроки', 'Скорость')
    return categoryShortNames[normalized] || normalized.charAt(0).toUpperCase()
  }

  useEffect(() => {
    // Проверяем токен при загрузке
    if (token) {
      checkAuth()
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      fetchAllPlans()
    }
  }, [isAuthenticated])

  const checkAuth = async (authToken = null) => {
    try {
      const tokenToUse = authToken || token || localStorage.getItem('token')
      if (!tokenToUse) {
        setIsAuthenticated(false)
        return
      }
      
      const response = await fetch('/api/users/me', {
        headers: {
          'Authorization': `Bearer ${tokenToUse}`
        }
      })
      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        setIsAuthenticated(true)
        if (!token) {
          setToken(tokenToUse)
        }
      } else {
        console.error('Ошибка проверки авторизации:', response.status, await response.text())
        localStorage.removeItem('token')
        setToken(null)
        setIsAuthenticated(false)
      }
    } catch (error) {
      console.error('Ошибка проверки авторизации:', error)
      localStorage.removeItem('token')
      setToken(null)
      setIsAuthenticated(false)
    }
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginError('')
    const formData = new FormData(e.target)
    const username = formData.get('username')
    const password = formData.get('password')

    try {
      const formDataToSend = new URLSearchParams()
      formDataToSend.append('username', username)
      formDataToSend.append('password', password)

      const response = await fetch('/api/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formDataToSend
      })

      const data = await response.json()

      if (response.ok && data.access_token) {
        const newToken = data.access_token
        setToken(newToken)
        localStorage.setItem('token', newToken)
        // Передаем токен напрямую в checkAuth
        await checkAuth(newToken)
      } else {
        setLoginError(data.detail || 'Ошибка входа')
      }
    } catch (error) {
      console.error('Ошибка входа:', error)
      setLoginError('Ошибка подключения к серверу: ' + error.message)
    }
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()
    setRegisterError('')

    try {
      const response = await fetch('/api/users/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          username: registerData.username,
          email: registerData.email || '',
          password: registerData.password,
          role: registerData.role || 'user'
        })
      })

      if (!response.ok) {
        let errorMessage = 'Ошибка создания пользователя'
        try {
          const data = await response.json()
          errorMessage = data.detail || errorMessage
        } catch (e) {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`
        }
        setRegisterError(errorMessage)
        return
      }

      const data = await response.json()
      
      // Обновляем список пользователей
      await fetchUsers()
      // Сбрасываем форму
      setRegisterData({ username: '', email: '', password: '', full_name: '', role: 'user' })
      setRegisterError('')
      setShowRegister(false)
    } catch (error) {
      console.error('Ошибка создания пользователя:', error)
      setRegisterError('Ошибка подключения к серверу: ' + error.message)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setIsAuthenticated(false)
    setUser(null)
    setShowUserManagement(false)
  }

  // Функции для администратора
  const isAdmin = user?.role === 'admin'

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/users', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      }
    } catch (error) {
      console.error('Ошибка при загрузке пользователей:', error)
    }
  }

  const updateUserRole = async (username, newRole) => {
    try {
      const response = await fetch(`/api/users/${username}/role?new_role=${newRole}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        await fetchUsers()
        if (username === user?.username) {
          await checkAuth(token)
        }
      }
    } catch (error) {
      console.error('Ошибка при изменении роли:', error)
    }
  }

  const updateUserStatus = async (username, isActive) => {
    try {
      const response = await fetch(`/api/users/${username}/status?is_active=${isActive}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        await fetchUsers()
      }
    } catch (error) {
      console.error('Ошибка при изменении статуса:', error)
    }
  }

  // Функции для управления разделами
  const fetchSections = async () => {
    try {
      const response = await fetch('/api/sections', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setSections(data.sections || [])
      }
    } catch (error) {
      console.error('Ошибка при загрузке разделов:', error)
    }
  }

  const createSection = async () => {
    if (!newSectionName.trim()) return
    try {
      const response = await fetch('/api/sections', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: newSectionName.trim() })
      })
      if (response.ok) {
        setNewSectionName('')
        await fetchSections()
        await fetchAllPlans()
      } else {
        const error = await response.json()
        alert(error.detail || 'Ошибка создания раздела')
      }
    } catch (error) {
      console.error('Ошибка при создании раздела:', error)
      alert('Ошибка при создании раздела')
    }
  }

  const deleteSection = async (sectionName) => {
    if (!confirm(`Удалить раздел "${sectionName}" со всеми характеристиками?`)) return
    try {
      const response = await fetch(`/api/sections/${encodeURIComponent(sectionName)}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        await fetchSections()
        await fetchAllPlans()
        if (selectedSectionForEdit === sectionName) {
          setSelectedSectionForEdit(null)
        }
      } else {
        const error = await response.json()
        alert(error.detail || 'Ошибка удаления раздела')
      }
    } catch (error) {
      console.error('Ошибка при удалении раздела:', error)
      alert('Ошибка при удалении раздела')
    }
  }

  const addCharacteristic = async () => {
    if (!selectedSectionForEdit || !newCharacteristic.name.trim()) return
    try {
      const response = await fetch(`/api/sections/${encodeURIComponent(selectedSectionForEdit)}/characteristics`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(newCharacteristic)
      })
      if (response.ok) {
        const sectionName = selectedSectionForEdit
        setNewCharacteristic({
          name: '',
          standard: '',
          expert: '',
          optimal: '',
          express: '',
          ultra: '',
          advantages: '',
          questions: '',
          personal_pain: '',
          corporate_pain: ''
        })
        setShowAddCharacteristic(false)
        await fetchSections()
        await fetchAllPlans()
        // Обновляем список характеристик
        await fetchSectionCharacteristics(sectionName)
      } else {
        const error = await response.json()
        alert(error.detail || 'Ошибка добавления характеристики')
      }
    } catch (error) {
      console.error('Ошибка при добавлении характеристики:', error)
      alert('Ошибка при добавлении характеристики')
    }
  }

  const deleteCharacteristic = async (sectionName, characteristicName) => {
    if (!confirm(`Удалить характеристику "${characteristicName}"?`)) return
    try {
      const response = await fetch(
        `/api/sections/${encodeURIComponent(sectionName)}/characteristics/${encodeURIComponent(characteristicName)}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      if (response.ok) {
        await fetchSections()
        await fetchAllPlans()
        // Обновляем список характеристик если раздел выбран
        if (selectedSectionForEdit === sectionName) {
          await fetchSectionCharacteristics(sectionName)
        }
      } else {
        const error = await response.json()
        alert(error.detail || 'Ошибка удаления характеристики')
      }
    } catch (error) {
      console.error('Ошибка при удалении характеристики:', error)
      alert('Ошибка при удалении характеристики')
    }
  }

  const fetchSectionCharacteristics = async (sectionName) => {
    try {
      const response = await fetch(`/api/sections/${encodeURIComponent(sectionName)}/characteristics`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setSectionCharacteristics(data.characteristics || [])
      }
    } catch (error) {
      console.error('Ошибка при загрузке характеристик:', error)
    }
  }

  const handleCharDragStart = (e, charName) => {
    if (!isAdmin) return
    setDraggedChar(charName)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleCharDragOver = (e, charName) => {
    if (!isAdmin || !draggedChar) return
    e.preventDefault()
    if (draggedChar !== charName) {
      setDragOverChar(charName)
    }
  }

  const handleCharDragLeave = () => {
    setDragOverChar(null)
  }

  const handleCharDrop = async (targetCharName) => {
    if (!isAdmin || !draggedChar || draggedChar === targetCharName || !selectedSectionForEdit) return
    
    const newOrder = [...sectionCharacteristics]
    const draggedIndex = newOrder.findIndex(c => c.name === draggedChar)
    const targetIndex = newOrder.findIndex(c => c.name === targetCharName)
    
    if (draggedIndex === -1 || targetIndex === -1) return
    
    const [removed] = newOrder.splice(draggedIndex, 1)
    newOrder.splice(targetIndex, 0, removed)
    
    setSectionCharacteristics(newOrder)
    setDraggedChar(null)
    setDragOverChar(null)
    
    // Сохраняем новый порядок на сервере
    try {
      const response = await fetch(`/api/sections/${encodeURIComponent(selectedSectionForEdit)}/characteristics/reorder`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ order: newOrder.map(c => c.name) })
      })
      if (response.ok) {
        await fetchAllPlans()
      }
    } catch (error) {
      console.error('Ошибка при сохранении порядка:', error)
    }
  }

  const handleCharDragEnd = () => {
    setDraggedChar(null)
    setDragOverChar(null)
  }

  // Функции для редактирования дашборда
  const startEditingInModal = () => {
    if (!isAdmin) return
    setEditingInModal(true)
    setModalEditValues({
      description: modalData?.описание || '',
      questions: modalData?.вопросы || '',
      ...Object.fromEntries(
        allPlans.map(plan => [`value_${plan.название}`, modalData?.значения[plan.название] || ''])
      )
    })
  }

  const cancelEditingInModal = () => {
    setEditingInModal(false)
    setModalEditValues({})
  }

  const saveEditInModal = async () => {
    if (!isAdmin || !modalData) return
    
    try {
      const updates = []
      
      // Обновление описания
      if (modalEditValues.description !== modalData.описание) {
        updates.push({
          section: modalData.раздел,
          characteristic: modalData.характеристика,
          new_value: modalEditValues.description,
          field_type: 'description'
        })
      }
      
      // Обновление вопросов
      if (modalEditValues.questions !== modalData.вопросы) {
        updates.push({
          section: modalData.раздел,
          characteristic: modalData.характеристика,
          new_value: modalEditValues.questions,
          field_type: 'questions'
        })
      }
      
      // Обновление значений тарифов
      for (const plan of allPlans) {
        const key = `value_${plan.название}`
        const newValue = modalEditValues[key]
        const oldValue = modalData.значения[plan.название] || ''
        if (newValue !== oldValue) {
          updates.push({
            section: modalData.раздел,
            characteristic: modalData.характеристика,
            plan_name: plan.название,
            new_value: newValue,
            field_type: 'value'
          })
        }
      }
      
      // Отправляем все обновления
      for (const update of updates) {
        const response = await fetch('/api/update-value', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(update)
        })
        if (!response.ok) {
          throw new Error(`Ошибка при сохранении: ${response.statusText}`)
        }
      }
      
      // Перезагружаем данные
      await fetchAllPlans()
      
      // Обновляем модальное окно
      const updatedChar = getAllCharacteristics().find(
        c => c.раздел === modalData.раздел && c.характеристика === modalData.характеристика
      )
      if (updatedChar) {
        setModalData(updatedChar)
      }
      
      setEditingInModal(false)
      setModalEditValues({})
    } catch (error) {
      console.error('Ошибка при сохранении изменений:', error)
      alert('Ошибка при сохранении изменений: ' + error.message)
    }
  }

  useEffect(() => {
    if (isAdmin && showUserManagement) {
      fetchUsers()
    }
  }, [isAdmin, showUserManagement])

  const fetchAllPlans = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/plans', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!response.ok) {
        if (response.status === 401) {
          handleLogout()
          return
        }
        throw new Error('Ошибка загрузки данных')
      }
      const data = await response.json()
      setAllPlans(data.plans || [])
      
      // Отладка: выводим все разделы
      if (data.plans && data.plans.length > 0) {
        const sectionsSet = new Set()
        data.plans.forEach(plan => {
          plan.характеристики.forEach(char => {
            if (char.раздел) {
              sectionsSet.add(char.раздел)
            }
          })
        })
        console.log('Загружено разделов:', sectionsSet.size)
        console.log('Разделы:', Array.from(sectionsSet).sort())
      }
    } catch (error) {
      console.error('Ошибка при загрузке всех тарифов:', error)
    } finally {
      setLoading(false)
    }
  }

  const togglePersonalCategory = (category) => {
    setPersonalCategories(prev => 
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    )
  }

  const toggleCorporateCategory = (category) => {
    setCorporateCategories(prev => 
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    )
  }

  const clearFilters = () => {
    setPersonalCategories([])
    setCorporateCategories([])
    setSelectedSection(null)
  }

  const showTooltip = (text, event) => {
    if (!text) return
    const rect = event.currentTarget.getBoundingClientRect()
    const tooltipWidth = 500 // примерная ширина tooltip
    const tooltipHeight = 200 // примерная высота tooltip
    const margin = 10
    
    // Вычисляем позицию по X с учетом границ экрана
    let x = rect.left + rect.width / 2
    if (x - tooltipWidth / 2 < margin) {
      x = tooltipWidth / 2 + margin
    } else if (x + tooltipWidth / 2 > window.innerWidth - margin) {
      x = window.innerWidth - tooltipWidth / 2 - margin
    }
    
    // Вычисляем позицию по Y с учетом границ экрана
    let y = rect.top - 10
    if (y - tooltipHeight < margin) {
      // Если не помещается сверху, показываем снизу
      y = rect.bottom + 10
    }
    
    setTooltip({
      show: true,
      text,
      x,
      y
    })
  }

  const hideTooltip = () => {
    setTooltip({ show: false, text: '', x: 0, y: 0 })
  }

  const openModal = (char) => {
    setModalData(char)
  }

  const closeModal = () => {
    setModalData(null)
  }


  // Получаем список всех разделов
  const getAllSections = () => {
    const sectionsSet = new Set()
    allPlans.forEach(plan => {
      plan.характеристики.forEach(char => {
        if (char.раздел && char.раздел.trim()) {
          sectionsSet.add(char.раздел.trim())
        }
      })
    })
    const sections = Array.from(sectionsSet).sort()
    console.log('Извлечено разделов из allPlans:', sections.length, sections)
    return sections
  }

  // Состояние для порядка разделов (только для админа)
  const [sectionOrder, setSectionOrder] = useState(() => {
    const saved = localStorage.getItem('sectionOrder')
    return saved ? JSON.parse(saved) : null
  })

  const rawSections = getAllSections()
  
  // Применяем сохраненный порядок или используем исходный
  const allSections = sectionOrder 
    ? sectionOrder.filter(section => rawSections.includes(section)).concat(
        rawSections.filter(section => !sectionOrder.includes(section))
      )
    : rawSections

  // Функции для drag and drop разделов (только для админа)
  const [draggedSection, setDraggedSection] = useState(null)
  const [dragOverSection, setDragOverSection] = useState(null)

  const handleDragStart = (e, section) => {
    if (!isAdmin) return
    setDraggedSection(section)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e, section) => {
    if (!isAdmin || !draggedSection) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (draggedSection !== section) {
      setDragOverSection(section)
    }
  }

  const handleDragLeave = () => {
    setDragOverSection(null)
  }

  const handleDrop = (e, targetSection) => {
    if (!isAdmin || !draggedSection || draggedSection === targetSection) return
    e.preventDefault()
    
    const newOrder = [...allSections]
    const draggedIndex = newOrder.indexOf(draggedSection)
    const targetIndex = newOrder.indexOf(targetSection)
    
    newOrder.splice(draggedIndex, 1)
    newOrder.splice(targetIndex, 0, draggedSection)
    
    setSectionOrder(newOrder)
    localStorage.setItem('sectionOrder', JSON.stringify(newOrder))
    setDraggedSection(null)
    setDragOverSection(null)
  }

  const handleDragEnd = () => {
    setDraggedSection(null)
    setDragOverSection(null)
  }

  const getAllCharacteristics = () => {
    const charMap = new Map()
    
    allPlans.forEach(plan => {
      plan.характеристики.forEach(char => {
        const key = `${char.раздел}|${char.характеристика}`
        if (!charMap.has(key)) {
          charMap.set(key, {
            раздел: char.раздел,
            характеристика: char.характеристика,
            описание: char.описание,
            личные_боли: char.личные_боли || '',
            корпоративные_боли: char.корпоративные_боли || '',
            возражения: char.возражения || '',
            сомнения: char.сомнения || '',
            вопросы: char.вопросы || '',
            is_section_header: char.is_section_header || false,
            значения: {},
            raw_значения: {}
          })
        }
        charMap.get(key).значения[plan.название] = char.значение || '-'
        charMap.get(key).raw_значения[plan.название] = char.raw_value || char.значение || '-'
      })
    })
    
    return Array.from(charMap.values())
  }

  const characteristics = getAllCharacteristics()
  
  // Извлекаем строки "Стоимость" и "Сроки" ДО фильтрации, чтобы они всегда были видны
  const seenHeaders = new Set()
  const stickyHeaders = []
  characteristics.forEach(char => {
    if (char.is_section_header && (char.характеристика === 'Стоимость' || char.характеристика === 'Сроки')) {
      if (!seenHeaders.has(char.характеристика)) {
        seenHeaders.add(char.характеристика)
        stickyHeaders.push(char) // Добавляем в sticky заголовки
      }
    }
  })
  
  // Сортируем sticky заголовки: сначала "Стоимость", потом "Сроки"
  stickyHeaders.sort((a, b) => {
    if (a.характеристика === 'Стоимость') return -1
    if (b.характеристика === 'Стоимость') return 1
    return 0
  })
  
  // Применяем все фильтры (исключая sticky заголовки)
  const filteredCharacteristics = characteristics.filter(char => {
    // Всегда показываем "Стоимость" и "Сроки"
    if (char.is_section_header && (char.характеристика === 'Стоимость' || char.характеристика === 'Сроки')) {
      return false // Убираем из основного списка, они уже в stickyHeaders
    }
    
    // Фильтр по разделу
    if (selectedSection && char.раздел !== selectedSection) {
      return false
    }
    
    // Фильтры по категориям болей (отдельно для личных и корпоративных)
    const hasPersonalFilter = personalCategories.length > 0
    const hasCorporateFilter = corporateCategories.length > 0
    
    if (hasPersonalFilter || hasCorporateFilter) {
      const normalizeCat = (cat) => {
        cat = cat.trim()
        cat = cat.replace('Лёгкость', 'Легкость').replace('Лекость', 'Легкость')
        cat = cat.replace('Безопасностьасность', 'Безопасность')
        cat = cat.replace('Безопасность, Безопасность', 'Безопасность')
        cat = cat.replace('Безопасность,Безопасность', 'Безопасность')
        cat = cat.replace('Безопастность', 'Безопасность')
        cat = cat.replace('Безоп', 'Безопасность')
        cat = cat.replace('Эконом', 'Экономия')
        cat = cat.replace('Сроки', 'Скорость')
        return cat
      }
      
      let matchesPersonal = false
      let matchesCorporate = false
      
      // Проверяем личные боли
      if (hasPersonalFilter && char.личные_боли) {
        const charPersonalCats = char.личные_боли.split(',').map(normalizeCat)
        const normalizedPersonal = personalCategories.map(normalizeCat)
        matchesPersonal = normalizedPersonal.some(cat => charPersonalCats.includes(cat))
      }
      
      // Проверяем корпоративные боли
      if (hasCorporateFilter && char.корпоративные_боли) {
        const charCorporateCats = char.корпоративные_боли.split(',').map(normalizeCat)
        const normalizedCorporate = corporateCategories.map(normalizeCat)
        matchesCorporate = normalizedCorporate.some(cat => charCorporateCats.includes(cat))
      }
      
      // Логика: если выбраны оба типа — нужно совпадение хотя бы по одному
      // Если выбран только один тип — нужно совпадение по нему
      if (hasPersonalFilter && hasCorporateFilter) {
        // Оба фильтра активны — показываем если совпадает хотя бы один
        if (!matchesPersonal && !matchesCorporate) return false
      } else if (hasPersonalFilter) {
        if (!matchesPersonal) return false
      } else if (hasCorporateFilter) {
        if (!matchesCorporate) return false
      }
    }
    
    return true
  })

  // Сортируем характеристики по порядку разделов из allSections
  const sortedCharacteristics = [...filteredCharacteristics].sort((a, b) => {
    // Сначала заголовки разделов
    if (a.is_section_header && !b.is_section_header) return -1
    if (!a.is_section_header && b.is_section_header) return 1
    
    // Если оба заголовки разделов, сортируем по порядку из allSections
    if (a.is_section_header && b.is_section_header) {
      const aIndex = allSections.indexOf(a.раздел)
      const bIndex = allSections.indexOf(b.раздел)
      if (aIndex === -1 && bIndex === -1) return 0
      if (aIndex === -1) return 1
      if (bIndex === -1) return -1
      return aIndex - bIndex
    }
    
    // Если оба не заголовки, сортируем по разделу
    if (!a.is_section_header && !b.is_section_header) {
      const aIndex = allSections.indexOf(a.раздел)
      const bIndex = allSections.indexOf(b.раздел)
      if (aIndex === -1 && bIndex === -1) {
        // Если раздел не найден в списке, сортируем по алфавиту
        return (a.раздел || '').localeCompare(b.раздел || '')
      }
      if (aIndex === -1) return 1
      if (bIndex === -1) return -1
      if (aIndex !== bIndex) {
        return aIndex - bIndex
      }
      // Если раздел одинаковый, сохраняем оригинальный порядок из API (не сортируем)
      return 0
    }
    
    return 0
  })

  const mainCharacteristics = sortedCharacteristics
  
  // Сортируем sticky заголовки: сначала "Стоимость", потом "Сроки"
  stickyHeaders.sort((a, b) => {
    if (a.характеристика === 'Стоимость') return -1
    if (b.характеристика === 'Стоимость') return 1
    return 0
  })

  // Функция для проверки, является ли значение чистым числом (без текста)
  const isPureNumber = (value) => {
    if (!value || value === '-' || value === '+') return false
    // Проверяем, что значение состоит только из цифр (возможно с пробелами)
    const trimmed = value.toString().trim()
    return /^\d+$/.test(trimmed)
  }

  // Функция для извлечения числового значения из строки
  const extractNumber = (value) => {
    if (!value || value === '-' || value === '+') return null
    const match = value.match(/(\d+)/)
    return match ? parseFloat(match[1]) : null
  }

  // Функция для расчета прогресса (для стоимости и числовых значений)
  const calculateProgress = (value, allValues, isPrice = false) => {
    if (!value || value === '-' || value === '+') return null
    
    // Для чистых чисел используем прямое значение
    let currentNum = null
    if (typeof value === 'number') {
      currentNum = value
    } else if (typeof value === 'string') {
      const trimmed = value.trim()
      if (/^\d+$/.test(trimmed)) {
        currentNum = parseFloat(trimmed)
      } else {
        currentNum = extractNumber(value)
      }
    } else {
      currentNum = extractNumber(value)
    }
    
    if (currentNum === null) return null
    
    const numbers = allValues
      .map(v => {
        if (typeof v === 'number') return v
        if (typeof v === 'string' && /^\d+$/.test(v.trim())) {
          return parseFloat(v.trim())
        }
        return extractNumber(v)
      })
      .filter(n => n !== null && !isNaN(n))
    
    if (numbers.length === 0) return null
    
    const max = Math.max(...numbers)
    const min = Math.min(...numbers)
    
    if (max === min) return 100
    
    if (isPrice) {
      // Для стоимости: чем больше, тем больше прогресс (больше стоимость = больше заполнение)
      return ((currentNum - min) / (max - min)) * 100
    } else {
      // Для остальных: чем больше, тем лучше (больше число = больше прогресс)
      return ((currentNum - min) / (max - min)) * 100
    }
  }

  const formatValue = (value, char, planName, allPlans) => {
    if (!value || value === '-') return <span className="value-empty">—</span>
    if (value === '+') return <span className="value-check">✓</span>
    
    // Проверяем, является ли это заголовком секции
    const isHeader = char.is_section_header
    const isPrice = char.характеристика === 'Стоимость'
    
    // Проверяем, является ли значение числовым в разделе "Срочность"
    const isSrochnostNumeric = char.раздел === 'Срочность' && isPureNumber(value)
    
    // Получаем все raw значения для расчета прогресса (используем raw_значения если есть)
    const allValues = allPlans.map(p => {
      const rawVal = char.raw_значения && char.raw_значения[p.название]
      return rawVal || char.значения[p.название]
    })
    
    // Используем raw значение для расчета прогресса
    const rawValue = char.raw_значения && char.raw_значения[planName]
    const valueForProgress = rawValue || value
    const progress = calculateProgress(valueForProgress, allValues, isPrice)
    
    // Показываем прогресс-бар для заголовков секций или для числовых значений в разделе "Срочность"
    const showProgress = (isHeader || isSrochnostNumeric) && progress !== null
    
    return (
      <div className="value-with-progress">
        <span className="value-text">{value}</span>
        {showProgress && (
          <div className="progress-bar-container">
            <div 
              className={`progress-bar ${isPrice ? 'progress-inverse' : ''}`}
              style={{ 
                width: `${Math.max(5, Math.min(100, progress))}%`,
                backgroundColor: isPrice 
                  ? (progress > 70 ? '#f97316' : progress > 40 ? '#fbbf24' : '#10b981')
                  : (progress > 70 ? '#10b981' : progress > 40 ? '#3b82f6' : '#8b5cf6')
              }}
            ></div>
          </div>
        )}
      </div>
    )
  }

  const activeFiltersCount = personalCategories.length + corporateCategories.length + (selectedSection ? 1 : 0)

  // Если не авторизован, показываем форму входа/регистрации
  if (!isAuthenticated) {
    return (
      <div className="auth-container">
        <div className="auth-box">
          <h1 className="auth-title">HPV Dashboard</h1>
          <form onSubmit={handleLogin} className="auth-form">
            <h2>Вход</h2>
            {loginError && <div className="auth-error">{loginError}</div>}
            <div className="auth-field">
              <label>Имя пользователя</label>
              <input type="text" name="username" required />
            </div>
            <div className="auth-field">
              <label>Пароль</label>
              <input type="password" name="password" required />
            </div>
            <button type="submit" className="auth-submit">Войти</button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="app-table">
      {/* Tooltip */}
      {tooltip.show && (
        <div 
          className="tooltip"
          style={{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }}
        >
          {tooltip.text}
          <div className="tooltip-arrow"></div>
        </div>
      )}

      {/* Modal */}
      {modalData && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>×</button>
            <div className="modal-header">
              <h2 className="modal-title">{modalData.характеристика}</h2>
              {isAdmin && !editingInModal && (
                <button className="modal-edit-btn" onClick={startEditingInModal}>
                  ✏️ Редактировать
                </button>
              )}
            </div>
            <div className="modal-section">
              <h3>Раздел</h3>
              <p>{modalData.раздел}</p>
            </div>
            {(modalData.личные_боли || modalData.корпоративные_боли) && (
              <div className="modal-section">
                <h3>Боли</h3>
                {modalData.личные_боли && (
                  <div className="modal-pain">
                    <span className="modal-label">Личные:</span>
                    <span className="pain-badge personal">{modalData.личные_боли}</span>
                  </div>
                )}
                {modalData.корпоративные_боли && (
                  <div className="modal-pain">
                    <span className="modal-label">Корпоративные:</span>
                    <span className="pain-badge corporate">{modalData.корпоративные_боли}</span>
                  </div>
                )}
              </div>
            )}
            <div className="modal-section">
              <h3>Преимущества</h3>
              {editingInModal ? (
                <textarea
                  className="modal-textarea-large"
                  value={modalEditValues.description}
                  onChange={(e) => setModalEditValues({...modalEditValues, description: e.target.value})}
                  rows={6}
                  placeholder="Введите преимущества..."
                />
              ) : (
                <p className="modal-text-large">
                  {modalData.описание || '—'}
                </p>
              )}
            </div>
            <div className="modal-section">
              <h3>Вопросы для клиента</h3>
              {editingInModal ? (
                <textarea
                  className="modal-textarea-large"
                  value={modalEditValues.questions}
                  onChange={(e) => setModalEditValues({...modalEditValues, questions: e.target.value})}
                  rows={6}
                  placeholder="Введите вопросы для клиента..."
                />
              ) : (
                <p className="modal-text-large">
                  {modalData.вопросы || '—'}
                </p>
              )}
            </div>
            {modalData.возражения && (
              <div className="modal-section">
                <h3>Возражения</h3>
                <p className="modal-objections">{modalData.возражения}</p>
              </div>
            )}
            <div className="modal-section">
              <h3>Значения по тарифам</h3>
              <div className="modal-plans">
                {allPlans.map(plan => (
                  <div key={plan.название} className="modal-plan-item">
                    <span className="modal-plan-name">{plan.название}:</span>
                    {editingInModal ? (
                      <input
                        type="text"
                        className="modal-input"
                        value={modalEditValues[`value_${plan.название}`] || ''}
                        onChange={(e) => setModalEditValues({
                          ...modalEditValues,
                          [`value_${plan.название}`]: e.target.value
                        })}
                      />
                    ) : (
                      <span className="modal-plan-value">
                        {modalData.значения[plan.название] || '—'}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
            {editingInModal && (
              <div className="modal-actions">
                <button className="modal-save-btn" onClick={saveEditInModal}>
                  💾 Сохранить
                </button>
                <button className="modal-cancel-btn" onClick={cancelEditingInModal}>
                  ✖ Отмена
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* User Management Modal */}
      {showUserManagement && isAdmin && (
        <div className="modal-overlay" onClick={() => setShowUserManagement(false)}>
          <div className="modal-content user-management-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowUserManagement(false)}>×</button>
            <h2 className="modal-title">Управление пользователями</h2>
            
            {/* Форма создания нового пользователя */}
            <div className="create-user-form">
              <h3>Создать нового пользователя</h3>
              <form onSubmit={handleCreateUser}>
                {registerError && <div className="auth-error">{registerError}</div>}
                <div className="form-row">
                  <div className="form-field">
                    <label>Имя пользователя *</label>
                    <input 
                      type="text" 
                      value={registerData.username}
                      onChange={(e) => setRegisterData({...registerData, username: e.target.value})}
                      required 
                    />
                  </div>
                  <div className="form-field">
                    <label>Email</label>
                    <input 
                      type="email" 
                      value={registerData.email}
                      onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-field">
                    <label>Пароль *</label>
                    <input 
                      type="password" 
                      value={registerData.password}
                      onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                      required 
                    />
                  </div>
                  <div className="form-field">
                    <label>Роль</label>
                    <select
                      value={registerData.role}
                      onChange={(e) => setRegisterData({...registerData, role: e.target.value})}
                    >
                      <option value="user">Пользователь</option>
                      <option value="admin">Администратор</option>
                    </select>
                  </div>
                </div>
                <button type="submit" className="create-user-btn">Создать пользователя</button>
              </form>
            </div>

            <div className="users-list">
              <h3>Список пользователей</h3>
              {users.map(u => (
                <div key={u.username} className="user-item">
                  <div className="user-info-item">
                    <div className="user-name-item">{u.username}</div>
                    <div className="user-email-item">{u.email || '—'}</div>
                    <div className="user-fullname-item">{u.full_name || '—'}</div>
                  </div>
                  <div className="user-controls">
                    <select
                      className="user-role-select"
                      value={u.role}
                      onChange={(e) => updateUserRole(u.username, e.target.value)}
                      disabled={u.username === user?.username}
                    >
                      <option value="user">Пользователь</option>
                      <option value="admin">Администратор</option>
                    </select>
                    <button
                      className={`user-status-btn ${u.is_active ? 'active' : 'blocked'}`}
                      onClick={() => updateUserStatus(u.username, !u.is_active)}
                      disabled={u.username === user?.username}
                    >
                      {u.is_active ? '🔓 Разблокирован' : '🔒 Заблокирован'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно управления разделами */}
      {showSectionManagement && (
        <div className="modal-overlay" onClick={() => setShowSectionManagement(false)}>
          <div className="section-management-modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowSectionManagement(false)}>×</button>
            <h2>Управление разделами</h2>
            
            {/* Создание нового раздела */}
            <div className="section-create-form">
              <h3>Создать новый раздел</h3>
              <div className="section-create-row">
                <input
                  type="text"
                  placeholder="Название раздела"
                  value={newSectionName}
                  onChange={e => setNewSectionName(e.target.value)}
                  className="section-input"
                />
                <button onClick={createSection} className="btn-create-section">
                  + Создать
                </button>
              </div>
            </div>

            {/* Список разделов */}
            <div className="sections-list">
              <h3>Существующие разделы ({sections.length})</h3>
              {sections.map(section => (
                <div key={section.name} className={`section-item ${selectedSectionForEdit === section.name ? 'selected' : ''}`}>
                  <div 
                    className="section-item-info" 
                    onClick={() => {
                      if (selectedSectionForEdit === section.name) {
                        setSelectedSectionForEdit(null)
                        setSectionCharacteristics([])
                      } else {
                        setSelectedSectionForEdit(section.name)
                        fetchSectionCharacteristics(section.name)
                      }
                    }}
                  >
                    <span className="section-name">{section.name}</span>
                    <span className="section-count">{section.characteristics_count} характеристик</span>
                    <span className="section-expand">{selectedSectionForEdit === section.name ? '▼' : '▶'}</span>
                  </div>
                  <div className="section-item-actions">
                    <button 
                      className="btn-add-char"
                      onClick={(e) => { e.stopPropagation(); setSelectedSectionForEdit(section.name); fetchSectionCharacteristics(section.name); setShowAddCharacteristic(true); }}
                    >
                      + Характеристика
                    </button>
                    <button 
                      className="btn-delete-section"
                      onClick={(e) => { e.stopPropagation(); deleteSection(section.name); }}
                    >
                      Удалить раздел
                    </button>
                  </div>
                  
                  {/* Список характеристик раздела */}
                  {selectedSectionForEdit === section.name && sectionCharacteristics.length > 0 && (
                    <div className="characteristics-list">
                      <div className="characteristics-header">
                        <span>Характеристики (перетащите для сортировки)</span>
                      </div>
                      {sectionCharacteristics.map(char => (
                        <div 
                          key={char.name}
                          className={`characteristic-item ${draggedChar === char.name ? 'dragging' : ''} ${dragOverChar === char.name ? 'drag-over' : ''}`}
                          draggable={isAdmin}
                          onDragStart={(e) => handleCharDragStart(e, char.name)}
                          onDragOver={(e) => handleCharDragOver(e, char.name)}
                          onDragLeave={handleCharDragLeave}
                          onDrop={() => handleCharDrop(char.name)}
                          onDragEnd={handleCharDragEnd}
                        >
                          <span className="char-drag-handle">⋮⋮</span>
                          <span className="char-name">{char.name}</span>
                          <div className="char-pains">
                            {char.personal_pain && <span className="pain-tag personal" title="Личные боли">{char.personal_pain}</span>}
                            {char.corporate_pain && <span className="pain-tag corporate" title="Корпоративные боли">{char.corporate_pain}</span>}
                          </div>
                          <button 
                            className="btn-delete-char"
                            onClick={() => deleteCharacteristic(section.name, char.name)}
                            title="Удалить характеристику"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Форма добавления характеристики */}
            {showAddCharacteristic && selectedSectionForEdit && (
              <div className="add-characteristic-form">
                <h3>Добавить характеристику в "{selectedSectionForEdit}"</h3>
                
                <div className="char-form-field">
                  <label>Название характеристики *</label>
                  <input
                    type="text"
                    value={newCharacteristic.name}
                    onChange={e => setNewCharacteristic({...newCharacteristic, name: e.target.value})}
                    placeholder="Например: Скорость обработки"
                  />
                </div>

                <div className="char-form-row">
                  <div className="char-form-field">
                    <label>Стандарт</label>
                    <input
                      type="text"
                      value={newCharacteristic.standard}
                      onChange={e => setNewCharacteristic({...newCharacteristic, standard: e.target.value})}
                      placeholder="Значение или + для галочки"
                    />
                  </div>
                  <div className="char-form-field">
                    <label>Эксперт</label>
                    <input
                      type="text"
                      value={newCharacteristic.expert}
                      onChange={e => setNewCharacteristic({...newCharacteristic, expert: e.target.value})}
                      placeholder="Значение или + для галочки"
                    />
                  </div>
                  <div className="char-form-field">
                    <label>Оптима</label>
                    <input
                      type="text"
                      value={newCharacteristic.optimal}
                      onChange={e => setNewCharacteristic({...newCharacteristic, optimal: e.target.value})}
                      placeholder="Значение или + для галочки"
                    />
                  </div>
                  <div className="char-form-field">
                    <label>Экспресс</label>
                    <input
                      type="text"
                      value={newCharacteristic.express}
                      onChange={e => setNewCharacteristic({...newCharacteristic, express: e.target.value})}
                      placeholder="Значение или + для галочки"
                    />
                  </div>
                  <div className="char-form-field">
                    <label>Ультра</label>
                    <input
                      type="text"
                      value={newCharacteristic.ultra}
                      onChange={e => setNewCharacteristic({...newCharacteristic, ultra: e.target.value})}
                      placeholder="Значение или + для галочки"
                    />
                  </div>
                </div>

                <div className="char-form-field">
                  <label>Преимущества / Описание</label>
                  <textarea
                    value={newCharacteristic.advantages}
                    onChange={e => setNewCharacteristic({...newCharacteristic, advantages: e.target.value})}
                    placeholder="Опишите преимущества этой характеристики"
                    rows={3}
                  />
                </div>

                <div className="char-form-field">
                  <label>Вопросы для клиента</label>
                  <textarea
                    value={newCharacteristic.questions}
                    onChange={e => setNewCharacteristic({...newCharacteristic, questions: e.target.value})}
                    placeholder="Вопросы, которые менеджер может задать клиенту"
                    rows={3}
                  />
                </div>

                <div className="char-form-row">
                  <div className="char-form-field">
                    <label>Боли личные</label>
                    <div className="pain-checkboxes">
                      {categories.map(cat => (
                        <label key={`personal-${cat}`} className="pain-checkbox">
                          <input
                            type="checkbox"
                            checked={newCharacteristic.personal_pain.includes(cat)}
                            onChange={e => {
                              const pains = newCharacteristic.personal_pain.split(',').filter(p => p.trim())
                              if (e.target.checked) {
                                pains.push(cat)
                              } else {
                                const idx = pains.indexOf(cat)
                                if (idx > -1) pains.splice(idx, 1)
                              }
                              setNewCharacteristic({...newCharacteristic, personal_pain: pains.join(', ')})
                            }}
                          />
                          {cat}
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="char-form-field">
                    <label>Боли корпоративные</label>
                    <div className="pain-checkboxes">
                      {categories.map(cat => (
                        <label key={`corporate-${cat}`} className="pain-checkbox">
                          <input
                            type="checkbox"
                            checked={newCharacteristic.corporate_pain.includes(cat)}
                            onChange={e => {
                              const pains = newCharacteristic.corporate_pain.split(',').filter(p => p.trim())
                              if (e.target.checked) {
                                pains.push(cat)
                              } else {
                                const idx = pains.indexOf(cat)
                                if (idx > -1) pains.splice(idx, 1)
                              }
                              setNewCharacteristic({...newCharacteristic, corporate_pain: pains.join(', ')})
                            }}
                          />
                          {cat}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="char-form-actions">
                  <button onClick={addCharacteristic} className="btn-save-char">
                    Добавить характеристику
                  </button>
                  <button onClick={() => setShowAddCharacteristic(false)} className="btn-cancel-char">
                    Отмена
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <header className="app-header">
        {/* Верхняя строка: логотип, настройки колонок, пользователь */}
        <div className="header-top">
          <div className="header-brand">
            <span className="logo">ХПВ</span>
            <span className="logo-subtitle">Дашборд</span>
          </div>
          
          <div className="header-columns-toggle">
            <label className="toggle-switch">
              <input 
                type="checkbox" 
                checked={showAdvantages} 
                onChange={() => setShowAdvantages(!showAdvantages)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Преимущества</span>
            </label>
            <label className="toggle-switch">
              <input 
                type="checkbox" 
                checked={showQuestions} 
                onChange={() => setShowQuestions(!showQuestions)}
              />
              <span className="toggle-slider"></span>
              <span className="toggle-label">Вопросы</span>
            </label>
          </div>

          <div className="header-user">
            <span className="user-name">{user?.username}</span>
            {user?.role === 'admin' && (
              <>
                <button className="btn-admin" onClick={() => { setShowSectionManagement(true); fetchSections(); }}>
                  Разделы
                </button>
                <button className="btn-admin" onClick={() => setShowUserManagement(true)}>
                  Пользователи
                </button>
              </>
            )}
            <button className="btn-logout" onClick={handleLogout}>Выйти</button>
          </div>
        </div>

        {/* Нижняя строка: фильтры */}
        <div className="header-filters">
          <div className="filter-group personal">
            <div className="filter-group-header">Боли личные</div>
            <div className="filter-group-buttons">
              {categories.map(category => {
                const isSelected = personalCategories.includes(category)
                return (
                  <button
                    key={`personal-${category}`}
                    className={`filter-chip ${isSelected ? 'active' : ''}`}
                    onClick={() => togglePersonalCategory(category)}
                  >
                    {category}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="filter-group corporate">
            <div className="filter-group-header">Боли корпоративные</div>
            <div className="filter-group-buttons">
              {categories.map(category => {
                const isSelected = corporateCategories.includes(category)
                return (
                  <button
                    key={`corporate-${category}`}
                    className={`filter-chip ${isSelected ? 'active' : ''}`}
                    onClick={() => toggleCorporateCategory(category)}
                  >
                    {category}
                  </button>
                )
              })}
            </div>
          </div>

          {activeFiltersCount > 0 && (
            <button className="btn-clear-filters" onClick={clearFilters}>
              Сбросить фильтры ({activeFiltersCount})
            </button>
          )}
        </div>
      </header>

      <div className="content-wrapper">
        <div className="sidebar-filters">
          <div className="sidebar-title">
            Разделы
            {isAdmin && (
              <span className="drag-hint" title="Перетащите разделы для изменения порядка">
                ⋮⋮
              </span>
            )}
          </div>
          <button
            className={`sidebar-filter-btn ${selectedSection === null ? 'active' : 'inactive'}`}
            onClick={() => setSelectedSection(null)}
          >
            Все разделы
          </button>
          {allSections.map((section, idx) => (
            <button
              key={idx}
              className={`sidebar-filter-btn ${selectedSection === section ? 'active' : 'inactive'} ${isAdmin ? 'draggable' : ''} ${draggedSection === section ? 'dragging' : ''} ${dragOverSection === section ? 'drag-over' : ''}`}
              onClick={() => !isAdmin && setSelectedSection(selectedSection === section ? null : section)}
              onMouseDown={(e) => {
                if (isAdmin && e.button === 0) {
                  // Разрешаем клик только если не начали перетаскивание
                  setTimeout(() => {
                    if (!draggedSection) {
                      setSelectedSection(selectedSection === section ? null : section)
                    }
                  }, 100)
                }
              }}
              draggable={isAdmin}
              onDragStart={(e) => handleDragStart(e, section)}
              onDragOver={(e) => handleDragOver(e, section)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, section)}
              onDragEnd={handleDragEnd}
            >
              {isAdmin && <span className="drag-handle">⋮⋮</span>}
              {section}
            </button>
          ))}
        </div>

        <div className="table-container">
          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
              <p>Загрузка...</p>
            </div>
          ) : (
            <>
              <div className="table-info">
                <span className="table-count">
                  Найдено: <strong>{mainCharacteristics.length + stickyHeaders.length}</strong>
                </span>
                {mainCharacteristics.length === 0 && stickyHeaders.length === 0 && (
                  <span className="table-empty-hint">
                    Измените фильтры для отображения результатов
                  </span>
                )}
              </div>
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th className="col-characteristic">Характеристика</th>
                    <th className="col-pain col-pain-personal" title="Личные боли: Л-Легкость, Б-Безопасность, С-Скорость, Э-Экономия">Личн.</th>
                    <th className="col-pain col-pain-corporate" title="Корпоративные боли: Л-Легкость, Б-Безопасность, С-Скорость, Э-Экономия">Корп.</th>
                    {showAdvantages && <th className="col-advantages">Преимущества</th>}
                    {showQuestions && <th className="col-questions">Вопросы</th>}
                    {allPlans.map(plan => (
                      <th key={plan.название} className="col-plan">
                        <div className="plan-header-cell">
                          <div className="plan-name">{plan.название}</div>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* Фиксированные строки "Стоимость" и "Сроки" */}
                  {stickyHeaders.map((char, idx) => {
                    const isFirstSticky = idx === 0
                    return (
                      <tr 
                        key={`sticky-${idx}`}
                        className={`table-row-clickable section-header-row sticky-header-row ${isFirstSticky ? 'sticky-first' : 'sticky-second'}`}
                      >
                        <td className={`cell-characteristic section-header-cell sticky-header-cell`}>
                          <div className={`char-name section-header-name`}>
                            {char.характеристика}
                          </div>
                        </td>
                        <td className={`cell-pain section-header-cell sticky-header-cell col-pain-personal`}></td>
                        <td className={`cell-pain section-header-cell sticky-header-cell col-pain-corporate`}></td>
                        {showAdvantages && (
                          <td className={`cell-advantages section-header-cell sticky-header-cell`}></td>
                        )}
                        {showQuestions && (
                          <td className={`cell-questions section-header-cell sticky-header-cell`}></td>
                        )}
                        {allPlans.map(plan => (
                          <td key={plan.название} className={`cell-plan section-header-cell sticky-header-cell`}>
                            {formatValue(char.значения[plan.название], char, plan.название, allPlans)}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                  {/* Основные характеристики */}
                  {mainCharacteristics.map((char, idx) => {
                    const isHeader = char.is_section_header
                    return (
                      <tr 
                        key={idx}
                        className={`table-row-clickable ${isHeader ? 'section-header-row' : ''}`}
                        onClick={(e) => {
                          if (!isHeader) {
                            openModal(char)
                          }
                        }}
                      >
                        <td className={`cell-characteristic ${isHeader ? 'section-header-cell' : ''}`}>
                          <div className="char-content-wrapper">
                            <div className={`char-name ${isHeader ? 'section-header-name' : ''}`}>
                              {char.характеристика}
                            </div>
                            {!isHeader && <div className="char-section">{char.раздел}</div>}
                            {!isHeader && (char.описание || char.вопросы || char.сомнения) && (
                              <div className="char-hints">
                                {char.описание && (
                                  <span 
                                    className="char-hint char-hint-advantages" 
                                    title={char.описание}
                                    onMouseEnter={(e) => showTooltip(char.описание, e)}
                                    onMouseLeave={hideTooltip}
                                  >
                                    П
                                  </span>
                                )}
                                {(char.вопросы || char.сомнения) && (
                                  <span 
                                    className="char-hint char-hint-questions"
                                    title={char.вопросы || char.сомнения}
                                    onMouseEnter={(e) => showTooltip(char.вопросы || char.сомнения, e)}
                                    onMouseLeave={hideTooltip}
                                  >
                                    В
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </td>
                        <td className={`cell-pain cell-pain-compact ${isHeader ? 'section-header-cell' : ''}`}>
                          {!isHeader && (
                            char.личные_боли ? (
                              <div className="pain-badges-compact">
                                {char.личные_боли.split(',').map((pain, idx) => (
                                  <span 
                                    key={idx} 
                                    className={`pain-badge-compact personal pain-${getCategoryShort(pain)}`}
                                    title={pain.trim()}
                                  >
                                    {getCategoryShort(pain)}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="pain-empty">—</span>
                            )
                          )}
                        </td>
                        <td className={`cell-pain cell-pain-compact ${isHeader ? 'section-header-cell' : ''}`}>
                          {!isHeader && (
                            char.корпоративные_боли ? (
                              <div className="pain-badges-compact">
                                {char.корпоративные_боли.split(',').map((pain, idx) => (
                                  <span 
                                    key={idx} 
                                    className={`pain-badge-compact corporate pain-${getCategoryShort(pain)}`}
                                    title={pain.trim()}
                                  >
                                    {getCategoryShort(pain)}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="pain-empty">—</span>
                            )
                          )}
                        </td>
                        {showAdvantages && (
                          <td className={`cell-advantages ${isHeader ? 'section-header-cell' : ''}`}>
                            {!isHeader && (
                              <div className="advantages-text" title={char.описание}>
                                {char.описание || '—'}
                              </div>
                            )}
                          </td>
                        )}
                        {showQuestions && (
                          <td className={`cell-questions ${isHeader ? 'section-header-cell' : ''}`}>
                            {!isHeader && (
                              (char.вопросы || char.сомнения) ? (
                                <div className="questions-text">
                                  {char.вопросы || char.сомнения}
                                </div>
                              ) : (
                                <span className="questions-empty">—</span>
                              )
                            )}
                          </td>
                        )}
                        {allPlans.map(plan => (
                          <td 
                            key={plan.название} 
                            className={`cell-plan ${isHeader ? 'section-header-cell' : ''}`}
                          >
                            {formatValue(char.значения[plan.название], char, plan.название, allPlans)}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
