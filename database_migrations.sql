/* Migration 0001 */
--
-- Create model Computer
--
CREATE TABLE `club_computer` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(50) NOT NULL, `status` varchar(20) NOT NULL);
--
-- Create model Tariff
--
CREATE TABLE `club_tariff` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(100) NOT NULL, `price_per_hour` numeric(8, 2) NOT NULL);
--
-- Create model Booking
--
CREATE TABLE `club_booking` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `start_time` datetime(6) NOT NULL, `end_time` datetime(6) NOT NULL, `created_at` datetime(6) NOT NULL, `user_id` integer NOT NULL, `computer_id` bigint NOT NULL, `tariff_id` bigint NOT NULL);
--
-- Create model Payment
--
CREATE TABLE `club_payment` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `amount` numeric(8, 2) NOT NULL, `paid_at` datetime(6) NOT NULL, `is_paid` bool NOT NULL, `booking_id` bigint NOT NULL);
ALTER TABLE `club_booking` ADD CONSTRAINT `club_booking_user_id_0ec6e8eb_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `club_booking` ADD CONSTRAINT `club_booking_computer_id_440c1097_fk_club_computer_id` FOREIGN KEY (`computer_id`) REFERENCES `club_computer` (`id`);
ALTER TABLE `club_booking` ADD CONSTRAINT `club_booking_tariff_id_6a1dab33_fk_club_tariff_id` FOREIGN KEY (`tariff_id`) REFERENCES `club_tariff` (`id`);
ALTER TABLE `club_payment` ADD CONSTRAINT `club_payment_booking_id_292f4e5a_fk_club_booking_id` FOREIGN KEY (`booking_id`) REFERENCES `club_booking` (`id`);

/* Migration 0002 */
--
-- Add field customer_name to booking
--
ALTER TABLE `club_booking` ADD COLUMN `customer_name` varchar(100) DEFAULT '═хт│фюьшщ ъы│║эЄ' NOT NULL;
ALTER TABLE `club_booking` ALTER COLUMN `customer_name` DROP DEFAULT;
--
-- Add field phone to booking
--
ALTER TABLE `club_booking` ADD COLUMN `phone` varchar(20) DEFAULT '═хт│фюьшщ ъы│║эЄ' NOT NULL;
ALTER TABLE `club_booking` ALTER COLUMN `phone` DROP DEFAULT;
--
-- Alter field user on booking
--
ALTER TABLE `club_booking` DROP FOREIGN KEY `club_booking_user_id_0ec6e8eb_fk_auth_user_id`;
ALTER TABLE `club_booking` MODIFY `user_id` integer NULL;
ALTER TABLE `club_booking` ADD CONSTRAINT `club_booking_user_id_0ec6e8eb_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

/* Migration 0003 */
--
-- Add field status to booking
--
ALTER TABLE `club_booking` ADD COLUMN `status` varchar(20) DEFAULT 'confirmed' NOT NULL;
ALTER TABLE `club_booking` ALTER COLUMN `status` DROP DEFAULT;
--
-- Add field liqpay_order_id to payment
--
ALTER TABLE `club_payment` ADD COLUMN `liqpay_order_id` varchar(255) NULL UNIQUE;
--
-- Add field status to payment
--
ALTER TABLE `club_payment` ADD COLUMN `status` varchar(40) DEFAULT 'pending' NOT NULL;
ALTER TABLE `club_payment` ALTER COLUMN `status` DROP DEFAULT;
--
-- Alter field paid_at on payment
--
ALTER TABLE `club_payment` MODIFY `paid_at` datetime(6) NULL;

/* Migration 0004 */
--
-- Add field payment_method to booking
--
ALTER TABLE `club_booking` ADD COLUMN `payment_method` varchar(10) DEFAULT 'cash' NOT NULL;
ALTER TABLE `club_booking` ALTER COLUMN `payment_method` DROP DEFAULT;
--
-- Add field payment_status to booking
--
ALTER TABLE `club_booking` ADD COLUMN `payment_status` varchar(10) DEFAULT 'unpaid' NOT NULL;
ALTER TABLE `club_booking` ALTER COLUMN `payment_status` DROP DEFAULT;

/* Migration 0005 */
--
-- Add field manual_occupied to computer
--
ALTER TABLE `club_computer` ADD COLUMN `manual_occupied` bool DEFAULT b'0' NOT NULL;
ALTER TABLE `club_computer` ALTER COLUMN `manual_occupied` DROP DEFAULT;

/* Migration 0006 */
--
-- Create model UserProfile
--
CREATE TABLE `club_userprofile` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `phone` varchar(20) NOT NULL, `user_id` integer NOT NULL UNIQUE);
ALTER TABLE `club_userprofile` ADD CONSTRAINT `club_userprofile_user_id_93bb733d_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

/* Migration 0007 */
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL

/* Migration 0008 */
--
-- Remove field liqpay_order_id from payment
--
ALTER TABLE `club_payment` DROP COLUMN `liqpay_order_id`;

/* Migration 0009 */
--
-- Alter field computer on booking
--
-- (no-op)
--
-- Alter field status on booking
--
-- (no-op)
--
-- Alter field tariff on booking
--
-- (no-op)
--
-- Alter field booking on payment
--
ALTER TABLE `club_payment` DROP FOREIGN KEY `club_payment_booking_id_292f4e5a_fk_club_booking_id`;
DROP INDEX `club_payment_booking_id_292f4e5a_uniq` ON `club_payment`;
ALTER TABLE `club_payment` MODIFY `booking_id` bigint NULL;
ALTER TABLE `club_payment` ADD CONSTRAINT `club_payment_booking_id_292f4e5a_uniq` UNIQUE (`booking_id`);
ALTER TABLE `club_payment` ADD CONSTRAINT `club_payment_booking_id_292f4e5a_fk_club_booking_id` FOREIGN KEY (`booking_id`) REFERENCES `club_booking` (`id`);

/* Migration 0010 */
--
-- Alter field payment_method on booking
--
-- (no-op)

/* Migration 0011 */
--
-- Alter field status on payment
--
-- (no-op)

