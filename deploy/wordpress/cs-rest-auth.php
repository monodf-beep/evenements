<?php
/*
Plugin Name: Cultura Sabauda — Auth REST par en-tête
Description: Authentifie l'API REST WordPress via l'en-tête HTTP « X-CS-Auth »
  (valeur = base64 de "identifiant:mot_de_passe_application") quand l'hébergeur
  supprime l'en-tête standard « Authorization » (erreur rest_not_logged_in).
  N'accepte QUE des mots de passe d'application valides — même niveau de sécurité
  que l'authentification WordPress native, juste via un en-tête que nginx/LiteSpeed
  ne filtre pas.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : déposer ce fichier dans  wp-content/mu-plugins/cs-rest-auth.php
  (créer le dossier mu-plugins s'il n'existe pas). Les « must-use plugins » sont
  actifs automatiquement, sans activation dans l'admin.
*/

if (!defined('ABSPATH')) { exit; }

add_filter('determine_current_user', function ($user) {
    // Si WordPress a déjà identifié quelqu'un (en-tête Authorization passé), on n'intervient pas.
    if (!empty($user)) {
        return $user;
    }
    // Les en-têtes personnalisés arrivent préfixés HTTP_ et en MAJUSCULES côté PHP.
    $raw = isset($_SERVER['HTTP_X_CS_AUTH']) ? trim($_SERVER['HTTP_X_CS_AUTH']) : '';
    if ($raw === '') {
        return $user;
    }
    $decoded = base64_decode($raw, true);
    if ($decoded === false || strpos($decoded, ':') === false) {
        return $user;
    }
    list($login, $password) = explode(':', $decoded, 2);
    if ($login === '' || $password === '') {
        return $user;
    }
    // Valide via le mécanisme natif des mots de passe d'application (gère les espaces).
    $result = wp_authenticate_application_password(null, $login, $password);
    if ($result instanceof WP_User) {
        return $result->ID;
    }
    return $user;
}, 20);
