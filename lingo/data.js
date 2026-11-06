// Курсы для русскоговорящих. w = [слово, перевод], p = [фраза, перевод]
const COURSES = {
  es: { name: 'Испанский', flag: '🇪🇸', speech: 'es-ES', color: '#ff9600', units: [
    { title: 'Основы', icon: '👋', w: [['hola','привет'],['adiós','пока'],['gracias','спасибо'],['por favor','пожалуйста'],['sí','да'],['no','нет'],['buenos días','доброе утро'],['buenas noches','спокойной ночи']],
      p: [['me llamo Ana','меня зовут Ана'],['¿cómo estás?','как ты'],['estoy muy bien','я очень хорошо']] },
    { title: 'Еда', icon: '🍎', w: [['manzana','яблоко'],['pan','хлеб'],['agua','вода'],['leche','молоко'],['queso','сыр'],['café','кофе'],['arroz','рис'],['pollo','курица']],
      p: [['quiero agua','я хочу воду'],['me gusta el café','мне нравится кофе'],['tengo una manzana','у меня есть яблоко']] },
    { title: 'Семья', icon: '👨‍👩‍👧', w: [['madre','мама'],['padre','папа'],['hermano','брат'],['hermana','сестра'],['abuelo','дедушка'],['abuela','бабушка'],['hijo','сын'],['hija','дочь']],
      p: [['mi madre es alta','моя мама высокая'],['tengo un hermano','у меня есть брат'],['ella es mi hermana','она моя сестра']] },
    { title: 'Животные', icon: '🐶', w: [['perro','собака'],['gato','кот'],['pájaro','птица'],['caballo','лошадь'],['pez','рыба'],['vaca','корова'],['conejo','кролик'],['oso','медведь']],
      p: [['el perro es grande','собака большая'],['tengo un gato','у меня есть кот'],['el pájaro canta','птица поёт']] }
  ]},
  fr: { name: 'Французский', flag: '🇫🇷', speech: 'fr-FR', color: '#1cb0f6', units: [
    { title: 'Основы', icon: '👋', w: [['bonjour','здравствуйте'],['salut','привет'],['merci','спасибо'],["s'il vous plaît",'пожалуйста'],['oui','да'],['non','нет'],['au revoir','до свидания'],['bonne nuit','спокойной ночи']],
      p: [["je m'appelle Marie",'меня зовут Мария'],['comment allez-vous','как вы поживаете'],['je vais très bien','у меня всё очень хорошо']] },
    { title: 'Еда', icon: '🥐', w: [['pomme','яблоко'],['pain','хлеб'],['eau','вода'],['lait','молоко'],['fromage','сыр'],['café','кофе'],['riz','рис'],['poulet','курица']],
      p: [["je veux de l'eau",'я хочу воды'],["j'aime le café",'я люблю кофе'],["j'ai une pomme",'у меня есть яблоко']] },
    { title: 'Семья', icon: '👨‍👩‍👧', w: [['mère','мама'],['père','папа'],['frère','брат'],['sœur','сестра'],['grand-père','дедушка'],['grand-mère','бабушка'],['fils','сын'],['fille','дочь']],
      p: [['ma mère est grande','моя мама высокая'],["j'ai un frère",'у меня есть брат'],['elle est ma sœur','она моя сестра']] },
    { title: 'Животные', icon: '🐱', w: [['chien','собака'],['chat','кот'],['oiseau','птица'],['cheval','лошадь'],['poisson','рыба'],['vache','корова'],['lapin','кролик'],['ours','медведь']],
      p: [['le chien est grand','собака большая'],["j'ai un chat",'у меня есть кот'],["l'oiseau chante",'птица поёт']] }
  ]},
  de: { name: 'Немецкий', flag: '🇩🇪', speech: 'de-DE', color: '#ce82ff', units: [
    { title: 'Основы', icon: '👋', w: [['hallo','привет'],['tschüss','пока'],['danke','спасибо'],['bitte','пожалуйста'],['ja','да'],['nein','нет'],['guten Morgen','доброе утро'],['gute Nacht','спокойной ночи']],
      p: [['ich heiße Anna','меня зовут Анна'],['wie geht es dir','как у тебя дела'],['mir geht es gut','у меня всё хорошо']] },
    { title: 'Еда', icon: '🥨', w: [['Apfel','яблоко'],['Brot','хлеб'],['Wasser','вода'],['Milch','молоко'],['Käse','сыр'],['Kaffee','кофе'],['Reis','рис'],['Hähnchen','курица']],
      p: [['ich möchte Wasser','я хочу воды'],['ich mag Kaffee','я люблю кофе'],['ich habe einen Apfel','у меня есть яблоко']] },
    { title: 'Семья', icon: '👨‍👩‍👧', w: [['Mutter','мама'],['Vater','папа'],['Bruder','брат'],['Schwester','сестра'],['Opa','дедушка'],['Oma','бабушка'],['Sohn','сын'],['Tochter','дочь']],
      p: [['meine Mutter ist groß','моя мама высокая'],['ich habe einen Bruder','у меня есть брат'],['sie ist meine Schwester','она моя сестра']] },
    { title: 'Животные', icon: '🐕', w: [['Hund','собака'],['Katze','кошка'],['Vogel','птица'],['Pferd','лошадь'],['Fisch','рыба'],['Kuh','корова'],['Hase','кролик'],['Bär','медведь']],
      p: [['der Hund ist groß','собака большая'],['ich habe eine Katze','у меня есть кошка'],['der Vogel singt','птица поёт']] }
  ]},
  en: { name: 'Английский', flag: '🇬🇧', speech: 'en-US', color: '#ff4b4b', units: [
    { title: 'Основы', icon: '👋', w: [['hello','привет'],['goodbye','до свидания'],['thanks','спасибо'],['please','пожалуйста'],['yes','да'],['no','нет'],['good morning','доброе утро'],['good night','спокойной ночи']],
      p: [['my name is Anna','меня зовут Анна'],['how are you','как дела'],['I am very well','у меня всё очень хорошо']] },
    { title: 'Еда', icon: '🍔', w: [['apple','яблоко'],['bread','хлеб'],['water','вода'],['milk','молоко'],['cheese','сыр'],['coffee','кофе'],['rice','рис'],['chicken','курица']],
      p: [['I want water','я хочу воды'],['I like coffee','я люблю кофе'],['I have an apple','у меня есть яблоко']] },
    { title: 'Семья', icon: '👨‍👩‍👧', w: [['mother','мама'],['father','папа'],['brother','брат'],['sister','сестра'],['grandfather','дедушка'],['grandmother','бабушка'],['son','сын'],['daughter','дочь']],
      p: [['my mother is tall','моя мама высокая'],['I have a brother','у меня есть брат'],['she is my sister','она моя сестра']] },
    { title: 'Животные', icon: '🐶', w: [['dog','собака'],['cat','кот'],['bird','птица'],['horse','лошадь'],['fish','рыба'],['cow','корова'],['rabbit','кролик'],['bear','медведь']],
      p: [['the dog is big','собака большая'],['I have a cat','у меня есть кот'],['the bird sings','птица поёт']] }
  ]}
};
