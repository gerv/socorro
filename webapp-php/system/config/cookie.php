/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

<?php defined('SYSPATH') or die('No direct script access.');
/**
 * @package  Core
 *
 * Domain, to restrict the cookie to a specific website domain. For security,
 * you are encouraged to set this option. An empty setting allows the cookie
 * to be read by any website domain.
 */
$config['domain'] = '';

/**
 * Restrict cookies to a specific path, typically the installation directory.
 */
$config['path'] = '/';

/**
 * Lifetime of the cookie. A setting of 0 makes the cookie active until the
 * users browser is closed or the cookie is deleted.
 */
$config['expire'] = 0;

/**
 * Enable this option to only allow the cookie to be read when using the a
 * secure protocol.
 */
$config['secure'] = FALSE;

/**
 * Enable this option to disable the cookie from being accessed when using a
 * secure protocol. This option is only available in PHP 5.2 and above.
 */
$config['httponly'] = FALSE;
